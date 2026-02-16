package port

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type ConditionRepository interface {
	Create(ctx context.Context, log *entity.ConditionLog) error
	List(ctx context.Context, from, to time.Time) ([]entity.ConditionLog, error)
	Delete(ctx context.Context, id int64) error
	GetTags(ctx context.Context) ([]string, error)
}

type DailySummaryRepository interface {
	Upsert(ctx context.Context, summary *entity.DailySummary) error
	GetByDate(ctx context.Context, date time.Time) (*entity.DailySummary, error)
	ListRange(ctx context.Context, from, to time.Time) ([]entity.DailySummary, error)
}

type HeartRateRepository interface {
	BulkUpsert(ctx context.Context, samples []entity.HeartRateSample) error
	ListRange(ctx context.Context, from, to time.Time) ([]entity.HeartRateSample, error)
}

type SleepStageRepository interface {
	BulkUpsert(ctx context.Context, stages []entity.SleepStage) error
	ListByDate(ctx context.Context, date time.Time) ([]entity.SleepStage, error)
}

type ExerciseRepository interface {
	Upsert(ctx context.Context, log *entity.ExerciseLog) error
	ListRange(ctx context.Context, from, to time.Time) ([]entity.ExerciseLog, error)
}

type TokenRepository interface {
	Get(ctx context.Context, provider string) (accessToken, refreshToken []byte, expiresAt time.Time, err error)
	Save(ctx context.Context, provider string, accessToken, refreshToken []byte, expiresAt time.Time) error
}

type PredictionRepository interface {
	Save(ctx context.Context, pred *entity.ConditionPrediction) error
	GetByDate(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error)
}
