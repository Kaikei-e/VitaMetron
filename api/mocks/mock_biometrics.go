package mocks

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type MockBiometricsProvider struct {
	ProviderNameFunc           func() string
	FetchDailySummaryFunc      func(ctx context.Context, date time.Time) (*entity.DailySummary, error)
	FetchHeartRateIntradayFunc func(ctx context.Context, date time.Time) ([]entity.HeartRateSample, error)
	FetchSleepStagesFunc       func(ctx context.Context, date time.Time) ([]entity.SleepStage, error)
	FetchExerciseLogsFunc      func(ctx context.Context, date time.Time) ([]entity.ExerciseLog, error)
	FetchHRVFunc               func(ctx context.Context, date time.Time) (float32, float32, error)
	FetchSpO2Func              func(ctx context.Context, date time.Time) (float32, float32, float32, error)
	FetchBreathingRateFunc     func(ctx context.Context, date time.Time) (float32, float32, float32, float32, error)
	FetchSkinTemperatureFunc   func(ctx context.Context, date time.Time) (float32, error)
}

func (m *MockBiometricsProvider) ProviderName() string {
	return m.ProviderNameFunc()
}

func (m *MockBiometricsProvider) FetchDailySummary(ctx context.Context, date time.Time) (*entity.DailySummary, error) {
	return m.FetchDailySummaryFunc(ctx, date)
}

func (m *MockBiometricsProvider) FetchHeartRateIntraday(ctx context.Context, date time.Time) ([]entity.HeartRateSample, error) {
	return m.FetchHeartRateIntradayFunc(ctx, date)
}

func (m *MockBiometricsProvider) FetchSleepStages(ctx context.Context, date time.Time) ([]entity.SleepStage, error) {
	return m.FetchSleepStagesFunc(ctx, date)
}

func (m *MockBiometricsProvider) FetchExerciseLogs(ctx context.Context, date time.Time) ([]entity.ExerciseLog, error) {
	return m.FetchExerciseLogsFunc(ctx, date)
}

func (m *MockBiometricsProvider) FetchHRV(ctx context.Context, date time.Time) (float32, float32, error) {
	return m.FetchHRVFunc(ctx, date)
}

func (m *MockBiometricsProvider) FetchSpO2(ctx context.Context, date time.Time) (float32, float32, float32, error) {
	return m.FetchSpO2Func(ctx, date)
}

func (m *MockBiometricsProvider) FetchBreathingRate(ctx context.Context, date time.Time) (float32, float32, float32, float32, error) {
	return m.FetchBreathingRateFunc(ctx, date)
}

func (m *MockBiometricsProvider) FetchSkinTemperature(ctx context.Context, date time.Time) (float32, error) {
	return m.FetchSkinTemperatureFunc(ctx, date)
}
