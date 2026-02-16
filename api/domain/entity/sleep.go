package entity

import "time"

type SleepRecord struct {
	LogID            int64
	StartTime        time.Time
	EndTime          time.Time
	DurationMin      int
	MinutesAsleep    int
	MinutesAwake     int
	OnsetLatencyMin  int
	Type             string // "stages" | "classic"
	DeepMin          int
	LightMin         int
	REMMin           int
	WakeMin          int
	IsMainSleep      bool
}

type SleepStage struct {
	Time    time.Time
	Stage   string // "deep" | "light" | "rem" | "wake"
	Seconds int
	LogID   int64
}
