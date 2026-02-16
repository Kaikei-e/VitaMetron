package entity

import (
	"encoding/json"
	"testing"
	"time"
)

func TestConditionPrediction_Fields(t *testing.T) {
	now := time.Now()
	factors, _ := json.Marshal(map[string]float64{
		"sleep_quality": 0.3,
		"resting_hr":    -0.2,
	})
	p := ConditionPrediction{
		TargetDate:          now,
		PredictedScore:      3.5,
		Confidence:          0.85,
		ContributingFactors: factors,
		RiskSignals:         []string{"low_hrv", "poor_sleep"},
		PredictedAt:         now,
	}
	if p.PredictedScore != 3.5 {
		t.Errorf("PredictedScore = %f, want 3.5", p.PredictedScore)
	}
	if p.Confidence != 0.85 {
		t.Errorf("Confidence = %f, want 0.85", p.Confidence)
	}
	if len(p.RiskSignals) != 2 {
		t.Errorf("len(RiskSignals) = %d, want 2", len(p.RiskSignals))
	}
}
