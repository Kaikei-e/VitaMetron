package application

import (
	"context"
	"time"

	"vitametron/api/domain/port"
)

type GetInsightsUseCase struct {
	predictor port.MLPredictor
}

func NewGetInsightsUseCase(predictor port.MLPredictor) *GetInsightsUseCase {
	return &GetInsightsUseCase{predictor: predictor}
}

func (uc *GetInsightsUseCase) GetWeeklyInsights(ctx context.Context, date time.Time) (*InsightsResult, error) {
	prediction, err := uc.predictor.PredictCondition(ctx, date)
	if err != nil {
		return nil, err
	}

	risks, err := uc.predictor.DetectRisk(ctx, date)
	if err != nil {
		return nil, err
	}

	return &InsightsResult{
		Prediction: prediction,
		Risks:      risks,
	}, nil
}
