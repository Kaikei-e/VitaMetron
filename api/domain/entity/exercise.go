package entity

import (
	"encoding/json"
	"time"
)

type ExerciseLog struct {
	ID           int64
	ExternalID   string
	ActivityName string
	StartedAt    time.Time
	DurationMS   int64
	Calories     int
	AvgHR        int
	DistanceKM   float32
	ZoneMinutes  json.RawMessage
	SyncedAt     time.Time
}
