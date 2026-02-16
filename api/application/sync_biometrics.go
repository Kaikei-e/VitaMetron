package application

import (
	"context"
	"log"
	"time"

	"vitametron/api/domain/port"
)

type SyncBiometricsUseCase struct {
	provider   port.BiometricsProvider
	summaryRepo port.DailySummaryRepository
	hrRepo     port.HeartRateRepository
	sleepRepo  port.SleepStageRepository
	exerciseRepo port.ExerciseRepository
}

func NewSyncBiometricsUseCase(
	provider port.BiometricsProvider,
	summaryRepo port.DailySummaryRepository,
	hrRepo port.HeartRateRepository,
	sleepRepo port.SleepStageRepository,
	exerciseRepo port.ExerciseRepository,
) *SyncBiometricsUseCase {
	return &SyncBiometricsUseCase{
		provider:     provider,
		summaryRepo:  summaryRepo,
		hrRepo:       hrRepo,
		sleepRepo:    sleepRepo,
		exerciseRepo: exerciseRepo,
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
		summary.HRVDailyRMSSD = dailyRMSSD
		summary.HRVDeepRMSSD = deepRMSSD
	} else {
		log.Printf("warn: FetchHRV failed for %s: %v", date.Format("2006-01-02"), err)
	}

	if avg, min, max, err := uc.provider.FetchSpO2(ctx, date); err == nil {
		summary.SpO2Avg = avg
		summary.SpO2Min = min
		summary.SpO2Max = max
	} else {
		log.Printf("warn: FetchSpO2 failed for %s: %v", date.Format("2006-01-02"), err)
	}

	if full, deep, light, rem, err := uc.provider.FetchBreathingRate(ctx, date); err == nil {
		summary.BRFullSleep = full
		summary.BRDeepSleep = deep
		summary.BRLightSleep = light
		summary.BRREMSleep = rem
	} else {
		log.Printf("warn: FetchBreathingRate failed for %s: %v", date.Format("2006-01-02"), err)
	}

	if temp, err := uc.provider.FetchSkinTemperature(ctx, date); err == nil {
		summary.SkinTempVariation = temp
	} else {
		log.Printf("warn: FetchSkinTemperature failed for %s: %v", date.Format("2006-01-02"), err)
	}

	// Upsert enriched summary
	if err := uc.summaryRepo.Upsert(ctx, summary); err != nil {
		return err
	}

	// Fetch and store HR intraday
	if hrSamples, err := uc.provider.FetchHeartRateIntraday(ctx, date); err == nil && len(hrSamples) > 0 {
		if err := uc.hrRepo.BulkUpsert(ctx, hrSamples); err != nil {
			log.Printf("warn: BulkUpsert HR failed for %s: %v", date.Format("2006-01-02"), err)
		}
	}

	// Fetch and store sleep stages
	if stages, err := uc.provider.FetchSleepStages(ctx, date); err == nil && len(stages) > 0 {
		if err := uc.sleepRepo.BulkUpsert(ctx, stages); err != nil {
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

	return nil
}
