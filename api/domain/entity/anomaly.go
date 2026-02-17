package entity

import (
	"encoding/json"
	"time"
)

type AnomalyDetection struct {
	Date                 time.Time       `json:"Date"`
	AnomalyScore         float32         `json:"AnomalyScore"`
	NormalizedScore      float32         `json:"NormalizedScore"`
	IsAnomaly            bool            `json:"IsAnomaly"`
	QualityGate          string          `json:"QualityGate"`
	QualityConfidence    float32         `json:"QualityConfidence"`
	QualityAdjustedScore float32         `json:"QualityAdjustedScore"`
	TopDrivers           json.RawMessage `json:"TopDrivers"`
	Explanation          string          `json:"Explanation"`
	ModelVersion         string          `json:"ModelVersion"`
	ComputedAt           time.Time       `json:"ComputedAt"`
}
