package port

import (
	"context"
	"io"
	"time"

	"vitametron/api/domain/entity"
)

type MLPredictor interface {
	PredictCondition(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error)
	DetectRisk(ctx context.Context, date time.Time) ([]string, error)
	PredictHRV(ctx context.Context, date time.Time) (*entity.HRVPrediction, error)
	TrainHRVModel(ctx context.Context, body io.Reader) (*entity.HRVTrainResult, error)
	GetHRVStatus(ctx context.Context) (*entity.HRVModelStatus, error)
	GetWeeklyInsights(ctx context.Context, date time.Time) (*entity.WeeklyInsight, error)
}
