package application

import (
	"context"
	"errors"
	"testing"
	"time"

	"vitametron/api/domain/entity"
	"vitametron/api/mocks"
)

func TestSyncBiometrics_AllSuccess(t *testing.T) {
	date := time.Date(2024, 1, 15, 0, 0, 0, 0, time.UTC)
	var upserted bool

	provider := &mocks.MockBiometricsProvider{
		FetchDailySummaryFunc: func(_ context.Context, _ time.Time) (*entity.DailySummary, error) {
			return &entity.DailySummary{Date: date, Steps: 10000}, nil
		},
		FetchHRVFunc: func(_ context.Context, _ time.Time) (float32, float32, error) {
			return 45.0, 55.0, nil
		},
		FetchSpO2Func: func(_ context.Context, _ time.Time) (float32, float32, float32, error) {
			return 97.5, 95.0, 99.0, nil
		},
		FetchBreathingRateFunc: func(_ context.Context, _ time.Time) (float32, float32, float32, float32, error) {
			return 15.5, 14.0, 16.0, 15.0, nil
		},
		FetchSkinTemperatureFunc: func(_ context.Context, _ time.Time) (float32, error) {
			return 0.5, nil
		},
		FetchHeartRateIntradayFunc: func(_ context.Context, _ time.Time) ([]entity.HeartRateSample, error) {
			return []entity.HeartRateSample{{BPM: 72}}, nil
		},
		FetchSleepStagesFunc: func(_ context.Context, _ time.Time) ([]entity.SleepStage, error) {
			return []entity.SleepStage{{Stage: "deep", Seconds: 300}}, nil
		},
		FetchExerciseLogsFunc: func(_ context.Context, _ time.Time) ([]entity.ExerciseLog, error) {
			return []entity.ExerciseLog{{ActivityName: "Running"}}, nil
		},
	}

	summaryRepo := &mocks.MockDailySummaryRepository{
		UpsertFunc: func(_ context.Context, s *entity.DailySummary) error {
			upserted = true
			if s.HRVDailyRMSSD != 45.0 {
				t.Errorf("HRVDailyRMSSD = %f, want 45.0", s.HRVDailyRMSSD)
			}
			if s.SpO2Avg != 97.5 {
				t.Errorf("SpO2Avg = %f, want 97.5", s.SpO2Avg)
			}
			return nil
		},
	}
	hrRepo := &mocks.MockHeartRateRepository{
		BulkUpsertFunc: func(_ context.Context, _ []entity.HeartRateSample) error { return nil },
	}
	sleepRepo := &mocks.MockSleepStageRepository{
		BulkUpsertFunc: func(_ context.Context, _ []entity.SleepStage) error { return nil },
	}
	exerciseRepo := &mocks.MockExerciseRepository{
		UpsertFunc: func(_ context.Context, _ *entity.ExerciseLog) error { return nil },
	}

	uc := NewSyncBiometricsUseCase(provider, summaryRepo, hrRepo, sleepRepo, exerciseRepo)
	if err := uc.SyncDate(context.Background(), date); err != nil {
		t.Fatalf("SyncDate() error = %v", err)
	}
	if !upserted {
		t.Error("summary was not upserted")
	}
}

func TestSyncBiometrics_PartialFetchFailure_Continues(t *testing.T) {
	date := time.Date(2024, 1, 15, 0, 0, 0, 0, time.UTC)

	provider := &mocks.MockBiometricsProvider{
		FetchDailySummaryFunc: func(_ context.Context, _ time.Time) (*entity.DailySummary, error) {
			return &entity.DailySummary{Date: date}, nil
		},
		FetchHRVFunc: func(_ context.Context, _ time.Time) (float32, float32, error) {
			return 0, 0, errors.New("hrv unavailable")
		},
		FetchSpO2Func: func(_ context.Context, _ time.Time) (float32, float32, float32, error) {
			return 0, 0, 0, errors.New("spo2 unavailable")
		},
		FetchBreathingRateFunc: func(_ context.Context, _ time.Time) (float32, float32, float32, float32, error) {
			return 0, 0, 0, 0, errors.New("br unavailable")
		},
		FetchSkinTemperatureFunc: func(_ context.Context, _ time.Time) (float32, error) {
			return 0, errors.New("temp unavailable")
		},
		FetchHeartRateIntradayFunc: func(_ context.Context, _ time.Time) ([]entity.HeartRateSample, error) {
			return nil, errors.New("hr unavailable")
		},
		FetchSleepStagesFunc: func(_ context.Context, _ time.Time) ([]entity.SleepStage, error) {
			return nil, errors.New("sleep unavailable")
		},
		FetchExerciseLogsFunc: func(_ context.Context, _ time.Time) ([]entity.ExerciseLog, error) {
			return nil, errors.New("exercise unavailable")
		},
	}

	summaryRepo := &mocks.MockDailySummaryRepository{
		UpsertFunc: func(_ context.Context, _ *entity.DailySummary) error { return nil },
	}
	hrRepo := &mocks.MockHeartRateRepository{}
	sleepRepo := &mocks.MockSleepStageRepository{}
	exerciseRepo := &mocks.MockExerciseRepository{}

	uc := NewSyncBiometricsUseCase(provider, summaryRepo, hrRepo, sleepRepo, exerciseRepo)
	if err := uc.SyncDate(context.Background(), date); err != nil {
		t.Fatalf("SyncDate() should succeed with partial failures, got error = %v", err)
	}
}

func TestSyncBiometrics_DailySummaryFetchError_ReturnsImmediately(t *testing.T) {
	provider := &mocks.MockBiometricsProvider{
		FetchDailySummaryFunc: func(_ context.Context, _ time.Time) (*entity.DailySummary, error) {
			return nil, errors.New("auth error")
		},
	}

	uc := NewSyncBiometricsUseCase(provider, nil, nil, nil, nil)
	err := uc.SyncDate(context.Background(), time.Now())
	if err == nil {
		t.Error("SyncDate() expected error, got nil")
	}
}
