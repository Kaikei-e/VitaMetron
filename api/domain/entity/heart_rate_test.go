package entity

import (
	"testing"
	"time"
)

func TestHeartRateSample_Fields(t *testing.T) {
	now := time.Now()
	s := HeartRateSample{
		Time:       now,
		BPM:        72,
		Confidence: 3,
	}
	if s.BPM != 72 {
		t.Errorf("BPM = %d, want 72", s.BPM)
	}
	if s.Confidence != 3 {
		t.Errorf("Confidence = %d, want 3", s.Confidence)
	}
}
