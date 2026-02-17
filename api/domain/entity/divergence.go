package entity

import (
	"encoding/json"
	"time"
)

type DivergenceDetection struct {
	Date           time.Time       `json:"Date"`
	ConditionLogID int64           `json:"ConditionLogID"`
	ActualScore    float32         `json:"ActualScore"`
	PredictedScore float32         `json:"PredictedScore"`
	Residual       float32         `json:"Residual"`
	CuSumPositive  float32         `json:"CuSumPositive"`
	CuSumNegative  float32         `json:"CuSumNegative"`
	CuSumAlert     bool            `json:"CuSumAlert"`
	DivergenceType string          `json:"DivergenceType"`
	Confidence     float32         `json:"Confidence"`
	TopDrivers     json.RawMessage `json:"TopDrivers"`
	Explanation    string          `json:"Explanation"`
	ModelVersion   string          `json:"ModelVersion"`
	ComputedAt     time.Time       `json:"ComputedAt"`
}

type DivergenceModelStatus struct {
	IsReady        bool     `json:"IsReady"`
	ModelVersion   string   `json:"ModelVersion"`
	TrainingPairs  int      `json:"TrainingPairs"`
	MinPairsNeeded int      `json:"MinPairsNeeded"`
	R2Score        *float64 `json:"R2Score"`
	MAE            *float64 `json:"MAE"`
	Phase          string   `json:"Phase"`
	Message        string   `json:"Message"`
}

type DivergenceTrainResult struct {
	ModelVersion      string   `json:"ModelVersion"`
	TrainingPairsUsed int      `json:"TrainingPairsUsed"`
	R2Score           *float64 `json:"R2Score"`
	MAE               *float64 `json:"MAE"`
	RMSE              *float64 `json:"RMSE"`
	Message           string   `json:"Message"`
}
