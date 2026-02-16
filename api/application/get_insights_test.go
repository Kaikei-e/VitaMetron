package application

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"vitametron/api/domain/entity"
	"vitametron/api/mocks"
)

func TestGetInsights_Success(t *testing.T) {
	date := time.Date(2024, 1, 15, 0, 0, 0, 0, time.UTC)

	predictor := &mocks.MockMLPredictor{
		PredictConditionFunc: func(_ context.Context, _ time.Time) (*entity.ConditionPrediction, error) {
			return &entity.ConditionPrediction{
				PredictedScore:      3.5,
				Confidence:          0.85,
				ContributingFactors: json.RawMessage(`{"sleep": 0.4}`),
			}, nil
		},
		DetectRiskFunc: func(_ context.Context, _ time.Time) ([]string, error) {
			return []string{"low_hrv"}, nil
		},
	}

	uc := NewGetInsightsUseCase(predictor)
	result, err := uc.GetWeeklyInsights(context.Background(), date)
	if err != nil {
		t.Fatalf("GetWeeklyInsights() error = %v", err)
	}
	if result.Prediction.PredictedScore != 3.5 {
		t.Errorf("PredictedScore = %f, want 3.5", result.Prediction.PredictedScore)
	}
	if len(result.Risks) != 1 || result.Risks[0] != "low_hrv" {
		t.Errorf("Risks = %v, want [low_hrv]", result.Risks)
	}
}

func TestGetInsights_PredictError(t *testing.T) {
	predictor := &mocks.MockMLPredictor{
		PredictConditionFunc: func(_ context.Context, _ time.Time) (*entity.ConditionPrediction, error) {
			return nil, errors.New("ml error")
		},
	}

	uc := NewGetInsightsUseCase(predictor)
	_, err := uc.GetWeeklyInsights(context.Background(), time.Now())
	if err == nil {
		t.Error("GetWeeklyInsights() expected error, got nil")
	}
}

func TestGetInsights_DetectRiskError(t *testing.T) {
	predictor := &mocks.MockMLPredictor{
		PredictConditionFunc: func(_ context.Context, _ time.Time) (*entity.ConditionPrediction, error) {
			return &entity.ConditionPrediction{PredictedScore: 3.0}, nil
		},
		DetectRiskFunc: func(_ context.Context, _ time.Time) ([]string, error) {
			return nil, errors.New("risk detection failed")
		},
	}

	uc := NewGetInsightsUseCase(predictor)
	_, err := uc.GetWeeklyInsights(context.Background(), time.Now())
	if err == nil {
		t.Error("GetWeeklyInsights() expected error, got nil")
	}
}
