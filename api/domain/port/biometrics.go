package port

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type BiometricsProvider interface {
	ProviderName() string
	FetchDailySummary(ctx context.Context, date time.Time) (*entity.DailySummary, error)
	FetchHeartRateIntraday(ctx context.Context, date time.Time) ([]entity.HeartRateSample, error)
	FetchSleepStages(ctx context.Context, date time.Time) ([]entity.SleepStage, error)
	FetchExerciseLogs(ctx context.Context, date time.Time) ([]entity.ExerciseLog, error)
	FetchHRV(ctx context.Context, date time.Time) (float32, float32, error)
	FetchSpO2(ctx context.Context, date time.Time) (avg, min, max float32, err error)
	FetchBreathingRate(ctx context.Context, date time.Time) (full, deep, light, rem float32, err error)
	FetchSkinTemperature(ctx context.Context, date time.Time) (float32, error)
}
