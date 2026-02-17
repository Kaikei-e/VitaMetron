package entity

import (
	"encoding/json"
	"time"
)

type HRVPrediction struct {
	Date               time.Time       `json:"Date"`
	TargetDate         time.Time       `json:"TargetDate"`
	PredictedZScore    float64         `json:"PredictedZScore"`
	PredictedDirection string          `json:"PredictedDirection"`
	Confidence         float64         `json:"Confidence"`
	TopDrivers         json.RawMessage `json:"TopDrivers"`
	ModelVersion       string          `json:"ModelVersion"`
	ComputedAt         time.Time       `json:"ComputedAt"`
}

type HRVTrainResult struct {
	ModelVersion          string
	TrainingDaysUsed      int
	CVMAE                 float64
	CVRMSE                float64
	CVR2                  float64
	CVDirectionalAccuracy float64
	Message               string
}

type HRVModelStatus struct {
	IsReady        bool               `json:"IsReady"`
	ModelVersion   string             `json:"ModelVersion"`
	TrainingDays   int                `json:"TrainingDays"`
	CVMetrics      map[string]float64 `json:"CVMetrics"`
	StableFeatures []string           `json:"StableFeatures"`
}
