package mocks

import (
	"context"
	"time"

	"vitametron/api/domain/entity"
)

type MockMLPredictor struct {
	PredictConditionFunc func(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error)
	DetectRiskFunc       func(ctx context.Context, date time.Time) ([]string, error)
}

func (m *MockMLPredictor) PredictCondition(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error) {
	return m.PredictConditionFunc(ctx, date)
}

func (m *MockMLPredictor) DetectRisk(ctx context.Context, date time.Time) ([]string, error) {
	return m.DetectRiskFunc(ctx, date)
}
