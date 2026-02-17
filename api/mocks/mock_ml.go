package mocks

import (
	"context"
	"io"
	"time"

	"vitametron/api/domain/entity"
)

type MockMLPredictor struct {
	PredictConditionFunc   func(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error)
	DetectRiskFunc         func(ctx context.Context, date time.Time) ([]string, error)
	PredictHRVFunc         func(ctx context.Context, date time.Time) (*entity.HRVPrediction, error)
	TrainHRVModelFunc      func(ctx context.Context, body io.Reader) (*entity.HRVTrainResult, error)
	GetHRVStatusFunc       func(ctx context.Context) (*entity.HRVModelStatus, error)
	GetWeeklyInsightsFunc  func(ctx context.Context, date time.Time) (*entity.WeeklyInsight, error)
}

func (m *MockMLPredictor) PredictCondition(ctx context.Context, date time.Time) (*entity.ConditionPrediction, error) {
	return m.PredictConditionFunc(ctx, date)
}

func (m *MockMLPredictor) DetectRisk(ctx context.Context, date time.Time) ([]string, error) {
	return m.DetectRiskFunc(ctx, date)
}

func (m *MockMLPredictor) PredictHRV(ctx context.Context, date time.Time) (*entity.HRVPrediction, error) {
	return m.PredictHRVFunc(ctx, date)
}

func (m *MockMLPredictor) TrainHRVModel(ctx context.Context, body io.Reader) (*entity.HRVTrainResult, error) {
	return m.TrainHRVModelFunc(ctx, body)
}

func (m *MockMLPredictor) GetHRVStatus(ctx context.Context) (*entity.HRVModelStatus, error) {
	return m.GetHRVStatusFunc(ctx)
}

func (m *MockMLPredictor) GetWeeklyInsights(ctx context.Context, date time.Time) (*entity.WeeklyInsight, error) {
	return m.GetWeeklyInsightsFunc(ctx, date)
}
