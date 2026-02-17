package application

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type ConditionUseCase interface {
	Create(ctx context.Context, log *entity.ConditionLog) error
	GetByID(ctx context.Context, id int64) (*entity.ConditionLog, error)
	List(ctx context.Context, filter entity.ConditionFilter) (*entity.ConditionListResult, error)
	Update(ctx context.Context, id int64, log *entity.ConditionLog) error
	Delete(ctx context.Context, id int64) error
	GetTags(ctx context.Context) ([]entity.TagCount, error)
	GetSummary(ctx context.Context, from, to time.Time) (*entity.ConditionSummary, error)
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
