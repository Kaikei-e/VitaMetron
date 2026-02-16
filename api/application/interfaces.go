package application

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type ConditionUseCase interface {
	Create(ctx context.Context, log *entity.ConditionLog) error
	List(ctx context.Context, from, to time.Time) ([]entity.ConditionLog, error)
	Delete(ctx context.Context, id int64) error
	GetTags(ctx context.Context) ([]string, error)
}

type SyncUseCase interface {
	SyncDate(ctx context.Context, date time.Time) error
}

type InsightsUseCase interface {
	GetWeeklyInsights(ctx context.Context, date time.Time) (*InsightsResult, error)
}

type InsightsResult struct {
	Prediction *entity.ConditionPrediction
	Risks      []string
}
