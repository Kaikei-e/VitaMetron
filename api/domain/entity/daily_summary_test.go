package entity

import (
	"testing"
	"time"
)

func TestDailySummary_FieldsExist(t *testing.T) {
	now := time.Now()
	ds := DailySummary{
		Date:              now,
		Provider:          "fitbit",
		RestingHR:         60,
		AvgHR:             72.5,
		MaxHR:             180,
		HRVDailyRMSSD:     45.0,
		HRVDeepRMSSD:      50.0,
		SpO2Avg:           97.5,
		SpO2Min:           95.0,
		SpO2Max:           99.0,
		BRFullSleep:       15.0,
		BRDeepSleep:       14.0,
		BRLightSleep:      16.0,
		BRREMSleep:        15.5,
		SkinTempVariation: 0.3,
		SleepStart:        &now,
		SleepEnd:          &now,
		SleepDurationMin:  480,
		SleepMinutesAsleep: 450,
		SleepMinutesAwake: 30,
		SleepOnsetLatency: 10,
		SleepType:         "stages",
		SleepDeepMin:      90,
		SleepLightMin:     200,
		SleepREMMin:       120,
		SleepWakeMin:      30,
		SleepIsMain:       true,
		Steps:             10000,
		DistanceKM:        7.5,
		Floors:            10,
		CaloriesTotal:     2500,
		CaloriesActive:    500,
		CaloriesBMR:       1800,
		ActiveZoneMin:     30,
		MinutesSedentary:  600,
		MinutesLightly:    200,
		MinutesFairly:     30,
		MinutesVery:       20,
		VO2Max:            44.5,
		HRZoneOutMin:      600,
		HRZoneFatMin:      120,
		HRZoneCardioMin:   30,
		HRZonePeakMin:     5,
		SyncedAt:          now,
	}

	if ds.Provider != "fitbit" {
		t.Errorf("Provider = %q, want %q", ds.Provider, "fitbit")
	}
	if ds.RestingHR != 60 {
		t.Errorf("RestingHR = %d, want 60", ds.RestingHR)
	}
	if ds.Steps != 10000 {
		t.Errorf("Steps = %d, want 10000", ds.Steps)
	}
}
