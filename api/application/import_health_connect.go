package application

import (
	"context"
	"log"
	"time"

	"vitametron/api/adapter/healthconnect"
	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

// ImportResult contains counts of imported records.
type ImportResult struct {
	DatesImported int `json:"dates_imported"`
	HRSamples     int `json:"hr_samples"`
	SleepStages   int `json:"sleep_stages"`
	ExerciseLogs  int `json:"exercise_logs"`
}

// ImportHealthConnectUseCase orchestrates Health Connect DB import.
type ImportHealthConnectUseCase struct {
	summaryRepo  port.DailySummaryRepository
	hrRepo       port.HeartRateRepository
	sleepRepo    port.SleepStageRepository
	exerciseRepo port.ExerciseRepository
}

func NewImportHealthConnectUseCase(
	summaryRepo port.DailySummaryRepository,
	hrRepo port.HeartRateRepository,
	sleepRepo port.SleepStageRepository,
	exerciseRepo port.ExerciseRepository,
) *ImportHealthConnectUseCase {
	return &ImportHealthConnectUseCase{
		summaryRepo:  summaryRepo,
		hrRepo:       hrRepo,
		sleepRepo:    sleepRepo,
		exerciseRepo: exerciseRepo,
	}
}

func (uc *ImportHealthConnectUseCase) Execute(ctx context.Context, dbPath string) (*ImportResult, error) {
	imp := &healthconnect.Importer{}
	data, err := imp.Extract(dbPath)
	if err != nil {
		return nil, err
	}

	result := &ImportResult{}

	// Upsert daily summaries one at a time
	for i := range data.Summaries {
		if err := uc.summaryRepo.Upsert(ctx, &data.Summaries[i]); err != nil {
			log.Printf("warn: upsert summary for %s: %v", data.Summaries[i].Date.Format("2006-01-02"), err)
			continue
		}
		result.DatesImported++
	}

	// Batch HR samples by day
	hrByDay := groupHRByDay(data.HRSamples)
	for day, samples := range hrByDay {
		if err := uc.hrRepo.BulkUpsert(ctx, samples); err != nil {
			log.Printf("warn: bulk upsert HR for %s: %v", day, err)
			continue
		}
		result.HRSamples += len(samples)
	}

	// Batch sleep stages by day — skip HC stages if Fitbit data already exists
	sleepByDay := groupSleepByDay(data.SleepStages)
	for day, stages := range sleepByDay {
		if len(stages) > 0 && stages[0].LogID == 0 {
			// HC stages have LogID 0 — check if Fitbit stages already exist for this range
			rangeEnd := stages[len(stages)-1].Time.Add(time.Duration(stages[len(stages)-1].Seconds) * time.Second)
			existing, err := uc.sleepRepo.ListByTimeRange(ctx, stages[0].Time, rangeEnd)
			if err == nil && hasFitbitStages(existing) {
				log.Printf("info: skipping HC sleep stages for %s — Fitbit data exists", day)
				continue
			}
		}
		if err := uc.sleepRepo.BulkUpsert(ctx, stages); err != nil {
			log.Printf("warn: bulk upsert sleep for %s: %v", day, err)
			continue
		}
		result.SleepStages += len(stages)
	}

	// Upsert exercises
	for i := range data.Exercises {
		if err := uc.exerciseRepo.Upsert(ctx, &data.Exercises[i]); err != nil {
			log.Printf("warn: upsert exercise %s: %v", data.Exercises[i].ExternalID, err)
			continue
		}
		result.ExerciseLogs++
	}

	return result, nil
}

func groupHRByDay(samples []entity.HeartRateSample) map[string][]entity.HeartRateSample {
	m := make(map[string][]entity.HeartRateSample)
	for _, s := range samples {
		day := s.Time.Format("2006-01-02")
		m[day] = append(m[day], s)
	}
	return m
}

func groupSleepByDay(stages []entity.SleepStage) map[string][]entity.SleepStage {
	m := make(map[string][]entity.SleepStage)
	for _, s := range stages {
		day := time.Date(s.Time.Year(), s.Time.Month(), s.Time.Day(), 0, 0, 0, 0, time.UTC).Format("2006-01-02")
		m[day] = append(m[day], s)
	}
	return m
}

func hasFitbitStages(stages []entity.SleepStage) bool {
	for _, s := range stages {
		if s.LogID != 0 {
			return true
		}
	}
	return false
}
