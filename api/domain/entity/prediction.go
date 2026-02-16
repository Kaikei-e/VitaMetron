package entity

import (
	"encoding/json"
	"time"
)

type ConditionPrediction struct {
	TargetDate          time.Time
	PredictedScore      float32
	Confidence          float32
	ContributingFactors json.RawMessage
	RiskSignals         []string
	PredictedAt         time.Time
}
