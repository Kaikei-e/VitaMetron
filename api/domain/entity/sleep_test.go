package entity

import (
	"testing"
	"time"
)

func TestSleepRecord_Fields(t *testing.T) {
	now := time.Now()
	r := SleepRecord{
		LogID:           12345,
		StartTime:       now,
		EndTime:         now.Add(8 * time.Hour),
		DurationMin:     480,
		MinutesAsleep:   420,
		MinutesAwake:    60,
		OnsetLatencyMin: 15,
		Type:            "stages",
		DeepMin:         90,
		LightMin:        180,
		REMMin:          120,
		WakeMin:         30,
		IsMainSleep:     true,
	}
	if r.Type != "stages" {
		t.Errorf("Type = %q, want %q", r.Type, "stages")
	}
	if !r.IsMainSleep {
		t.Error("IsMainSleep should be true")
	}
}

func TestSleepStage_Fields(t *testing.T) {
	now := time.Now()
	s := SleepStage{
		Time:    now,
		Stage:   "deep",
		Seconds: 300,
		LogID:   12345,
	}
	if s.Stage != "deep" {
		t.Errorf("Stage = %q, want %q", s.Stage, "deep")
	}
	if s.Seconds != 300 {
		t.Errorf("Seconds = %d, want 300", s.Seconds)
	}
}
