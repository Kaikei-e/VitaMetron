package entity

import "time"

type DailySummary struct {
	Date     time.Time
	Provider string

	// Heart rate
	RestingHR int
	AvgHR     float32
	MaxHR     int

	// HRV
	HRVDailyRMSSD float32
	HRVDeepRMSSD  float32

	// SpO2
	SpO2Avg float32
	SpO2Min float32
	SpO2Max float32

	// Breathing rate
	BRFullSleep float32
	BRDeepSleep float32
	BRLightSleep float32
	BRREMSleep  float32

	// Skin temperature
	SkinTempVariation float32

	// Sleep
	SleepStart        *time.Time
	SleepEnd          *time.Time
	SleepDurationMin  int
	SleepMinutesAsleep int
	SleepMinutesAwake int
	SleepOnsetLatency int
	SleepType         string
	SleepDeepMin      int
	SleepLightMin     int
	SleepREMMin       int
	SleepWakeMin      int
	SleepIsMain       bool

	// Activity
	Steps            int
	DistanceKM       float32
	Floors           int
	CaloriesTotal    int
	CaloriesActive   int
	CaloriesBMR      int
	ActiveZoneMin    int
	MinutesSedentary int
	MinutesLightly   int
	MinutesFairly    int
	MinutesVery      int

	// VO2 Max
	VO2Max float32

	// Heart rate zones
	HRZoneOutMin    int
	HRZoneFatMin    int
	HRZoneCardioMin int
	HRZonePeakMin   int

	SyncedAt time.Time
}
