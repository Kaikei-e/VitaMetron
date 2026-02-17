package application

import (
	"context"
	"errors"
	"testing"
	"time"

	"vitametron/api/domain/entity"
	"vitametron/api/mocks"
)

func newQualityRepo() *mocks.MockDataQualityRepository {
	return &mocks.MockDataQualityRepository{
		UpsertFunc: func(_ context.Context, _ *entity.DataQuality) error { return nil },
		GetByDateFunc: func(_ context.Context, _ time.Time) (*entity.DataQuality, error) {
			return nil, nil
		},
		ListRangeFunc: func(_ context.Context, _, _ time.Time) ([]entity.DataQuality, error) {
			return nil, nil
		},
		CountValidDaysFunc: func(_ context.Context, _ time.Time, _ int) (int, error) {
			return 0, nil
		},
	}
}

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
		FetchSleepStagesFunc: func(_ context.Context, _ time.Time) ([]entity.SleepStage, *entity.SleepRecord, error) {
			start := time.Date(2024, 1, 14, 23, 0, 0, 0, time.UTC)
			end := time.Date(2024, 1, 15, 7, 0, 0, 0, time.UTC)
			return []entity.SleepStage{{Stage: "deep", Seconds: 300}}, &entity.SleepRecord{
				StartTime:     start,
				EndTime:       end,
				DurationMin:   480,
				MinutesAsleep: 450,
				MinutesAwake:  30,
				Type:          "stages",
				DeepMin:       90,
				LightMin:      200,
				REMMin:        120,
				WakeMin:       30,
				IsMainSleep:   true,
			}, nil
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
			if s.SleepDurationMin != 480 {
				t.Errorf("SleepDurationMin = %d, want 480", s.SleepDurationMin)
			}
			if s.SleepDeepMin != 90 {
				t.Errorf("SleepDeepMin = %d, want 90", s.SleepDeepMin)
			}
			if s.SleepLightMin != 200 {
				t.Errorf("SleepLightMin = %d, want 200", s.SleepLightMin)
			}
			if s.SleepREMMin != 120 {
				t.Errorf("SleepREMMin = %d, want 120", s.SleepREMMin)
			}
			if s.SleepMinutesAsleep != 450 {
				t.Errorf("SleepMinutesAsleep = %d, want 450", s.SleepMinutesAsleep)
			}
			if !s.SleepIsMain {
				t.Error("SleepIsMain = false, want true")
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

	uc := NewSyncBiometricsUseCase(provider, summaryRepo, hrRepo, sleepRepo, exerciseRepo, newQualityRepo())
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
		FetchSleepStagesFunc: func(_ context.Context, _ time.Time) ([]entity.SleepStage, *entity.SleepRecord, error) {
			return nil, nil, errors.New("sleep unavailable")
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

	uc := NewSyncBiometricsUseCase(provider, summaryRepo, hrRepo, sleepRepo, exerciseRepo, newQualityRepo())
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

	uc := NewSyncBiometricsUseCase(provider, nil, nil, nil, nil, nil)
	err := uc.SyncDate(context.Background(), time.Now())
	if err == nil {
		t.Error("SyncDate() expected error, got nil")
	}
}

func TestSyncBiometrics_ComputesDataQuality(t *testing.T) {
	date := time.Date(2024, 1, 15, 0, 0, 0, 0, time.UTC)
	var qualityUpserted bool
	var capturedQuality *entity.DataQuality

	// Generate 600 HR samples (= 10 hours of wear)
	hrSamples := make([]entity.HeartRateSample, 600)
	for i := range hrSamples {
		hrSamples[i] = entity.HeartRateSample{BPM: 72}
	}

	provider := &mocks.MockBiometricsProvider{
		FetchDailySummaryFunc: func(_ context.Context, _ time.Time) (*entity.DailySummary, error) {
			return &entity.DailySummary{
				Date:              date,
				RestingHR:         62,
				HRVDailyRMSSD:    45.0,
				SpO2Avg:          97.0,
				SleepDurationMin:  420,
				Steps:            8000,
				BRFullSleep:       15.0,
				SkinTempVariation: 0.5,
			}, nil
		},
		FetchHRVFunc: func(_ context.Context, _ time.Time) (float32, float32, error) {
			return 45.0, 55.0, nil
		},
		FetchSpO2Func: func(_ context.Context, _ time.Time) (float32, float32, float32, error) {
			return 97.0, 95.0, 99.0, nil
		},
		FetchBreathingRateFunc: func(_ context.Context, _ time.Time) (float32, float32, float32, float32, error) {
			return 15.0, 14.0, 16.0, 15.0, nil
		},
		FetchSkinTemperatureFunc: func(_ context.Context, _ time.Time) (float32, error) {
			return 0.5, nil
		},
		FetchHeartRateIntradayFunc: func(_ context.Context, _ time.Time) ([]entity.HeartRateSample, error) {
			return hrSamples, nil
		},
		FetchSleepStagesFunc: func(_ context.Context, _ time.Time) ([]entity.SleepStage, *entity.SleepRecord, error) {
			return nil, nil, errors.New("no sleep data")
		},
		FetchExerciseLogsFunc: func(_ context.Context, _ time.Time) ([]entity.ExerciseLog, error) {
			return nil, nil
		},
	}

	summaryRepo := &mocks.MockDailySummaryRepository{
		UpsertFunc: func(_ context.Context, _ *entity.DailySummary) error { return nil },
	}
	hrRepo := &mocks.MockHeartRateRepository{
		BulkUpsertFunc: func(_ context.Context, _ []entity.HeartRateSample) error { return nil },
	}
	sleepRepo := &mocks.MockSleepStageRepository{}
	exerciseRepo := &mocks.MockExerciseRepository{}

	qualityRepo := &mocks.MockDataQualityRepository{
		UpsertFunc: func(_ context.Context, q *entity.DataQuality) error {
			qualityUpserted = true
			capturedQuality = q
			return nil
		},
		CountValidDaysFunc: func(_ context.Context, _ time.Time, _ int) (int, error) {
			return 30, nil
		},
		GetByDateFunc: func(_ context.Context, _ time.Time) (*entity.DataQuality, error) {
			return nil, nil
		},
		ListRangeFunc: func(_ context.Context, _, _ time.Time) ([]entity.DataQuality, error) {
			return nil, nil
		},
	}

	uc := NewSyncBiometricsUseCase(provider, summaryRepo, hrRepo, sleepRepo, exerciseRepo, qualityRepo)
	if err := uc.SyncDate(context.Background(), date); err != nil {
		t.Fatalf("SyncDate() error = %v", err)
	}

	if !qualityUpserted {
		t.Fatal("data quality was not upserted")
	}

	if capturedQuality.HRSampleCount != 600 {
		t.Errorf("HRSampleCount = %d, want 600", capturedQuality.HRSampleCount)
	}
	if capturedQuality.WearTimeHours != 10.0 {
		t.Errorf("WearTimeHours = %f, want 10.0", capturedQuality.WearTimeHours)
	}
	if !capturedQuality.PlausibilityPass {
		t.Error("PlausibilityPass = false, want true")
	}
	if !capturedQuality.IsValidDay {
		t.Error("IsValidDay = false, want true")
	}
	if capturedQuality.BaselineDays != 30 {
		t.Errorf("BaselineDays = %d, want 30", capturedQuality.BaselineDays)
	}
	if capturedQuality.BaselineMaturity != "warming" {
		t.Errorf("BaselineMaturity = %s, want warming", capturedQuality.BaselineMaturity)
	}
	if capturedQuality.CompletenessPct != 1.0 {
		t.Errorf("CompletenessPct = %f, want 1.0", capturedQuality.CompletenessPct)
	}
	if capturedQuality.ConfidenceScore <= 0 {
		t.Errorf("ConfidenceScore = %f, want > 0", capturedQuality.ConfidenceScore)
	}
}
