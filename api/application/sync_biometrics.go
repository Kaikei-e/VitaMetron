package application

import (
	"context"
	"log"
	"time"

	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type SyncBiometricsUseCase struct {
	provider     port.BiometricsProvider
	summaryRepo  port.DailySummaryRepository
	hrRepo       port.HeartRateRepository
	sleepRepo    port.SleepStageRepository
	exerciseRepo port.ExerciseRepository
	qualityRepo  port.DataQualityRepository
}

func NewSyncBiometricsUseCase(
	provider port.BiometricsProvider,
	summaryRepo port.DailySummaryRepository,
	hrRepo port.HeartRateRepository,
	sleepRepo port.SleepStageRepository,
	exerciseRepo port.ExerciseRepository,
	qualityRepo port.DataQualityRepository,
) *SyncBiometricsUseCase {
	return &SyncBiometricsUseCase{
		provider:     provider,
		summaryRepo:  summaryRepo,
		hrRepo:       hrRepo,
		sleepRepo:    sleepRepo,
		exerciseRepo: exerciseRepo,
		qualityRepo:  qualityRepo,
	}
}

func (uc *SyncBiometricsUseCase) SyncDate(ctx context.Context, date time.Time) error {
	// Fetch daily summary (includes activity, sleep summary, basic HR)
	summary, err := uc.provider.FetchDailySummary(ctx, date)
	if err != nil {
		return err
	}

	// Enrich with additional data, continue on individual fetch failures
	if dailyRMSSD, deepRMSSD, err := uc.provider.FetchHRV(ctx, date); err == nil {
		summary.HRVDailyRMSSD = entity.Float32Ptr(dailyRMSSD)
		summary.HRVDeepRMSSD = entity.Float32Ptr(deepRMSSD)
	} else {
		log.Printf("warn: FetchHRV failed for %s: %v", date.Format("2006-01-02"), err)
	}

	if avg, min, max, err := uc.provider.FetchSpO2(ctx, date); err == nil {
		summary.SpO2Avg = entity.Float32Ptr(avg)
		summary.SpO2Min = entity.Float32Ptr(min)
		summary.SpO2Max = entity.Float32Ptr(max)
	} else {
		log.Printf("warn: FetchSpO2 failed for %s: %v", date.Format("2006-01-02"), err)
	}

	if full, deep, light, rem, err := uc.provider.FetchBreathingRate(ctx, date); err == nil {
		summary.BRFullSleep = entity.Float32Ptr(full)
		summary.BRDeepSleep = entity.Float32Ptr(deep)
		summary.BRLightSleep = entity.Float32Ptr(light)
		summary.BRREMSleep = entity.Float32Ptr(rem)
	} else {
		log.Printf("warn: FetchBreathingRate failed for %s: %v", date.Format("2006-01-02"), err)
	}

	if temp, err := uc.provider.FetchSkinTemperature(ctx, date); err == nil {
		summary.SkinTempVariation = entity.Float32Ptr(temp)
	} else {
		log.Printf("warn: FetchSkinTemperature failed for %s: %v", date.Format("2006-01-02"), err)
	}

	// Fetch sleep stages + summary (before upsert so summary includes sleep data)
	var sleepStages []entity.SleepStage
	if stages, rec, err := uc.provider.FetchSleepStages(ctx, date); err == nil {
		sleepStages = stages
		if rec != nil {
			summary.SleepStart = &rec.StartTime
			summary.SleepEnd = &rec.EndTime
			summary.SleepDurationMin = rec.DurationMin
			summary.SleepMinutesAsleep = rec.MinutesAsleep
			summary.SleepMinutesAwake = rec.MinutesAwake
			summary.SleepType = rec.Type
			summary.SleepDeepMin = rec.DeepMin
			summary.SleepLightMin = rec.LightMin
			summary.SleepREMMin = rec.REMMin
			summary.SleepWakeMin = rec.WakeMin
			summary.SleepIsMain = rec.IsMainSleep
		}
	} else {
		log.Printf("warn: FetchSleepStages failed for %s: %v", date.Format("2006-01-02"), err)
	}

	// Upsert enriched summary (now includes sleep)
	if err := uc.summaryRepo.Upsert(ctx, summary); err != nil {
		return err
	}

	// Fetch and store HR intraday
	var hrSamples []entity.HeartRateSample
	if samples, err := uc.provider.FetchHeartRateIntraday(ctx, date); err == nil && len(samples) > 0 {
		hrSamples = samples
		if err := uc.hrRepo.BulkUpsert(ctx, hrSamples); err != nil {
			log.Printf("warn: BulkUpsert HR failed for %s: %v", date.Format("2006-01-02"), err)
		}
	}

	// Store granular sleep stages
	if len(sleepStages) > 0 {
		if err := uc.sleepRepo.BulkUpsert(ctx, sleepStages); err != nil {
			log.Printf("warn: BulkUpsert sleep stages failed for %s: %v", date.Format("2006-01-02"), err)
		}
	}

	// Fetch and store exercise logs
	if exercises, err := uc.provider.FetchExerciseLogs(ctx, date); err == nil {
		for i := range exercises {
			if err := uc.exerciseRepo.Upsert(ctx, &exercises[i]); err != nil {
				log.Printf("warn: Upsert exercise failed: %v", err)
			}
		}
	}

	// Compute and store data quality
	if uc.qualityRepo != nil {
		quality := uc.computeDataQuality(ctx, date, summary, hrSamples)
		if err := uc.qualityRepo.Upsert(ctx, quality); err != nil {
			log.Printf("warn: Upsert data quality failed for %s: %v", date.Format("2006-01-02"), err)
		}
	}

	return nil
}

func (uc *SyncBiometricsUseCase) computeDataQuality(
	ctx context.Context,
	date time.Time,
	summary *entity.DailySummary,
	hrSamples []entity.HeartRateSample,
) *entity.DataQuality {
	// Plausibility
	flags := entity.CheckPlausibility(summary)
	plausibilityPass := true
	for _, status := range flags {
		if status != "pass" && status != "missing" {
			plausibilityPass = false
			break
		}
	}

	// Completeness
	present, missing, completenessPct := entity.CheckMetricCompleteness(summary)

	// Wear time from HR sample count (each sample = 1 minute)
	hrSampleCount := len(hrSamples)
	wearTimeHours := float32(hrSampleCount) / 60.0

	// Valid day: wear_time >= 10h AND plausibility_pass
	isValidDay := wearTimeHours >= 10.0 && plausibilityPass

	// Baseline maturity
	baselineDays := 0
	if uc.qualityRepo != nil {
		if count, err := uc.qualityRepo.CountValidDays(ctx, date, 60); err == nil {
			baselineDays = count
		} else {
			log.Printf("warn: CountValidDays failed for %s: %v", date.Format("2006-01-02"), err)
		}
	}
	var baselineMaturity string
	switch {
	case baselineDays < 14:
		baselineMaturity = "cold"
	case baselineDays < 60:
		baselineMaturity = "warming"
	default:
		baselineMaturity = "mature"
	}

	// Composite confidence score
	wearNorm := wearTimeHours / 16.0
	if wearNorm > 1.0 {
		wearNorm = 1.0
	}
	baselineNorm := float32(baselineDays) / 60.0
	if baselineNorm > 1.0 {
		baselineNorm = 1.0
	}
	confidenceScore := 0.4*completenessPct + 0.3*wearNorm + 0.3*baselineNorm

	var confidenceLevel string
	switch {
	case confidenceScore < 0.4:
		confidenceLevel = "low"
	case confidenceScore <= 0.7:
		confidenceLevel = "medium"
	default:
		confidenceLevel = "high"
	}

	return &entity.DataQuality{
		Date:              date,
		WearTimeHours:     wearTimeHours,
		HRSampleCount:     hrSampleCount,
		CompletenessPct:   completenessPct,
		MetricsPresent:    present,
		MetricsMissing:    missing,
		PlausibilityFlags: flags,
		PlausibilityPass:  plausibilityPass,
		IsValidDay:        isValidDay,
		BaselineDays:      baselineDays,
		BaselineMaturity:  baselineMaturity,
		ConfidenceScore:   confidenceScore,
		ConfidenceLevel:   confidenceLevel,
		ComputedAt:        time.Now(),
	}
}
