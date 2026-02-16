package entity

import (
	"encoding/json"
	"testing"
	"time"
)

func TestExerciseLog_Fields(t *testing.T) {
	now := time.Now()
	e := ExerciseLog{
		ID:           1,
		ExternalID:   "fitbit-123",
		ActivityName: "Running",
		StartedAt:    now,
		DurationMS:   3600000,
		Calories:     500,
		AvgHR:        145,
		DistanceKM:   5.2,
		ZoneMinutes:  json.RawMessage(`{"fat_burn": 10, "cardio": 20}`),
		SyncedAt:     now,
	}
	if e.ActivityName != "Running" {
		t.Errorf("ActivityName = %q, want %q", e.ActivityName, "Running")
	}
	if e.DurationMS != 3600000 {
		t.Errorf("DurationMS = %d, want 3600000", e.DurationMS)
	}
}
