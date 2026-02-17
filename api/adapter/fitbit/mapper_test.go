package fitbit

import (
	"math"
	"testing"
	"time"
)

func TestParseVO2MaxRange(t *testing.T) {
	tests := []struct {
		input string
		want  *float64
	}{
		{"42.5-46.4", float64Ptr(44.45)},
		{"30.0-35.0", float64Ptr(32.5)},
		{"50.0", float64Ptr(50.0)},
		{"", nil},
		{"invalid", nil},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := ParseVO2MaxRange(tt.input)
			if tt.want == nil {
				if got != nil {
					t.Errorf("ParseVO2MaxRange(%q) = %f, want nil", tt.input, *got)
				}
				return
			}
			if got == nil {
				t.Fatalf("ParseVO2MaxRange(%q) = nil, want %f", tt.input, *tt.want)
			}
			if math.Abs(*got-*tt.want) > 0.01 {
				t.Errorf("ParseVO2MaxRange(%q) = %f, want %f", tt.input, *got, *tt.want)
			}
		})
	}
}

func TestMapSleepType(t *testing.T) {
	if MapSleepType("stages") != "stages" {
		t.Error("stages should map to stages")
	}
	if MapSleepType("classic") != "classic" {
		t.Error("classic should map to classic")
	}
	if MapSleepType("unknown") != "classic" {
		t.Error("unknown should map to classic")
	}
}

func TestMapSleepStage(t *testing.T) {
	tests := map[string]string{
		"deep":     "deep",
		"light":    "light",
		"rem":      "rem",
		"wake":     "wake",
		"restless": "wake",
		"asleep":   "light",
		"awake":    "wake",
	}
	for input, want := range tests {
		t.Run(input, func(t *testing.T) {
			if got := MapSleepStage(input); got != want {
				t.Errorf("MapSleepStage(%q) = %q, want %q", input, got, want)
			}
		})
	}
}

func TestMapActivityToSummary(t *testing.T) {
	resp := &ActivityResponse{}
	resp.Summary.Steps = 10000
	resp.Summary.CaloriesOut = 2500
	resp.Summary.CaloriesBMR = 1800
	resp.Summary.Floors = 12
	resp.Summary.RestingHeartRate = 62
	resp.Summary.SedentaryMinutes = 600
	resp.Summary.LightlyActiveMinutes = 180
	resp.Summary.FairlyActiveMinutes = 30
	resp.Summary.VeryActiveMinutes = 45
	resp.Summary.Distances = []struct {
		Activity string  `json:"activity"`
		Distance float64 `json:"distance"`
	}{
		{Activity: "total", Distance: 7.5},
		{Activity: "tracker", Distance: 7.5},
	}
	resp.Summary.HeartRateZones = []struct {
		Name    string `json:"name"`
		Minutes int    `json:"minutes"`
	}{
		{Name: "Out of Range", Minutes: 1000},
		{Name: "Fat Burn", Minutes: 200},
		{Name: "Cardio", Minutes: 50},
		{Name: "Peak", Minutes: 10},
	}

	date := time.Date(2025, 6, 15, 0, 0, 0, 0, time.UTC)
	s := mapActivityToSummary(resp, date)

	if s.Steps != 10000 {
		t.Errorf("Steps = %d, want 10000", s.Steps)
	}
	if s.CaloriesActive != 700 {
		t.Errorf("CaloriesActive = %d, want 700", s.CaloriesActive)
	}
	if s.DistanceKM != 7.5 {
		t.Errorf("DistanceKM = %f, want 7.5", s.DistanceKM)
	}
	if s.HRZoneOutMin != 1000 {
		t.Errorf("HRZoneOutMin = %d, want 1000", s.HRZoneOutMin)
	}
	if s.HRZoneFatMin != 200 {
		t.Errorf("HRZoneFatMin = %d, want 200", s.HRZoneFatMin)
	}
	if s.HRZoneCardioMin != 50 {
		t.Errorf("HRZoneCardioMin = %d, want 50", s.HRZoneCardioMin)
	}
	if s.HRZonePeakMin != 10 {
		t.Errorf("HRZonePeakMin = %d, want 10", s.HRZonePeakMin)
	}
	if s.Provider != "fitbit" {
		t.Errorf("Provider = %q, want fitbit", s.Provider)
	}
}

func TestMapSleepStages(t *testing.T) {
	resp := &SleepResponse{}
	resp.Sleep = []struct {
		LogID              int64  `json:"logId"`
		DateOfSleep        string `json:"dateOfSleep"`
		StartTime          string `json:"startTime"`
		EndTime            string `json:"endTime"`
		Duration           int64  `json:"duration"`
		MinutesAsleep      int    `json:"minutesAsleep"`
		MinutesAwake       int    `json:"minutesAwake"`
		MinutesAfterWakeup int    `json:"minutesAfterWakeup"`
		TimeInBed          int    `json:"timeInBed"`
		Type               string `json:"type"`
		IsMainSleep        bool   `json:"isMainSleep"`
		Levels             struct {
			Summary struct {
				Deep  *struct{ Minutes int `json:"minutes"` } `json:"deep"`
				Light *struct{ Minutes int `json:"minutes"` } `json:"light"`
				REM   *struct{ Minutes int `json:"minutes"` } `json:"rem"`
				Wake  *struct{ Minutes int `json:"minutes"` } `json:"wake"`
			} `json:"summary"`
			Data []struct {
				DateTime string `json:"dateTime"`
				Level    string `json:"level"`
				Seconds  int    `json:"seconds"`
			} `json:"data"`
		} `json:"levels"`
	}{
		{
			LogID:       12345,
			IsMainSleep: true,
			Levels: struct {
				Summary struct {
					Deep  *struct{ Minutes int `json:"minutes"` } `json:"deep"`
					Light *struct{ Minutes int `json:"minutes"` } `json:"light"`
					REM   *struct{ Minutes int `json:"minutes"` } `json:"rem"`
					Wake  *struct{ Minutes int `json:"minutes"` } `json:"wake"`
				} `json:"summary"`
				Data []struct {
					DateTime string `json:"dateTime"`
					Level    string `json:"level"`
					Seconds  int    `json:"seconds"`
				} `json:"data"`
			}{
				Data: []struct {
					DateTime string `json:"dateTime"`
					Level    string `json:"level"`
					Seconds  int    `json:"seconds"`
				}{
					{DateTime: "2025-06-15T23:00:00.000", Level: "light", Seconds: 300},
					{DateTime: "2025-06-15T23:05:00.000", Level: "deep", Seconds: 600},
				},
			},
		},
	}

	date := time.Date(2025, 6, 15, 0, 0, 0, 0, time.UTC)
	stages := mapSleepStages(resp, date)

	if len(stages) != 2 {
		t.Fatalf("len(stages) = %d, want 2", len(stages))
	}
	if stages[0].Stage != "light" {
		t.Errorf("stages[0].Stage = %q, want light", stages[0].Stage)
	}
	if stages[1].Stage != "deep" {
		t.Errorf("stages[1].Stage = %q, want deep", stages[1].Stage)
	}
	if stages[0].LogID != 12345 {
		t.Errorf("stages[0].LogID = %d, want 12345", stages[0].LogID)
	}
}

func TestMapHRIntraday(t *testing.T) {
	resp := &HRIntradayResponse{}
	resp.ActivitiesHeartIntraday.Dataset = []struct {
		Time  string `json:"time"`
		Value int    `json:"value"`
	}{
		{Time: "08:00:00", Value: 72},
		{Time: "08:01:00", Value: 75},
	}

	date := time.Date(2025, 6, 15, 0, 0, 0, 0, time.UTC)
	samples := mapHRIntraday(resp, date)

	if len(samples) != 2 {
		t.Fatalf("len(samples) = %d, want 2", len(samples))
	}
	if samples[0].BPM != 72 {
		t.Errorf("samples[0].BPM = %d, want 72", samples[0].BPM)
	}
	if samples[1].BPM != 75 {
		t.Errorf("samples[1].BPM = %d, want 75", samples[1].BPM)
	}
}

func TestMapExerciseLogs(t *testing.T) {
	resp := &ActivityResponse{}
	resp.Activities = []struct {
		LogID              int64   `json:"logId"`
		ActivityName       string  `json:"activityName"`
		StartTime          string  `json:"startTime"`
		Duration           int64   `json:"duration"`
		Calories           int     `json:"calories"`
		AverageHeartRate   int     `json:"averageHeartRate"`
		Distance           float64 `json:"distance"`
		DistanceUnit       string  `json:"distanceUnit"`
		ActiveZoneMinutes  *struct {
			TotalMinutes       int `json:"totalMinutes"`
			ActiveZoneMinutes  []struct {
				MinuteInZone int    `json:"minuteInZone"`
				Type         string `json:"type"`
			} `json:"activeZoneMinutes"`
		} `json:"activeZoneMinutes"`
	}{
		{
			LogID:            99999,
			ActivityName:     "Run",
			StartTime:        "07:30",
			Duration:         1800000,
			Calories:         350,
			AverageHeartRate: 145,
			Distance:         5.2,
		},
	}

	date := time.Date(2025, 6, 15, 0, 0, 0, 0, time.UTC)
	logs := mapExerciseLogs(resp, date)

	if len(logs) != 1 {
		t.Fatalf("len(logs) = %d, want 1", len(logs))
	}
	if logs[0].ExternalID != "99999" {
		t.Errorf("ExternalID = %q, want 99999", logs[0].ExternalID)
	}
	if logs[0].ActivityName != "Run" {
		t.Errorf("ActivityName = %q, want Run", logs[0].ActivityName)
	}
	if logs[0].Calories != 350 {
		t.Errorf("Calories = %d, want 350", logs[0].Calories)
	}
}

func float64Ptr(v float64) *float64 { return &v }
