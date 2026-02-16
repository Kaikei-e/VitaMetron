package port

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type MLPredictor interface {
	PredictCondition(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error)
	DetectRisk(ctx context.Context, date time.Time) ([]string, error)
}
