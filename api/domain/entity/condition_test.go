package entity

import (
	"testing"
	"time"
)

func intPtr(v int) *int { return &v }

func TestConditionLog_Validate_OK(t *testing.T) {
	tests := []struct {
		name string
		log  ConditionLog
	}{
		{"vas 0", ConditionLog{OverallVAS: 0, LoggedAt: time.Now()}},
		{"vas 50", ConditionLog{OverallVAS: 50, LoggedAt: time.Now()}},
		{"vas 100", ConditionLog{OverallVAS: 100, LoggedAt: time.Now()}},
		{"vas with all dimensions", ConditionLog{
			OverallVAS:      75,
			MoodVAS:         intPtr(60),
			EnergyVAS:       intPtr(80),
			SleepQualityVAS: intPtr(70),
			StressVAS:       intPtr(65),
			LoggedAt:        time.Now(),
		}},
		{"legacy fields with vas", ConditionLog{
			OverallVAS: 50,
			Overall:    3,
			Mental:     intPtr(2),
			Physical:   intPtr(4),
			Energy:     intPtr(5),
			LoggedAt:   time.Now(),
		}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if err := tt.log.Validate(); err != nil {
				t.Errorf("Validate() unexpected error: %v", err)
			}
		})
	}
}

func TestConditionLog_Validate_Error(t *testing.T) {
	longNote := make([]byte, 1001)
	for i := range longNote {
		longNote[i] = 'a'
	}

	manyTags := make([]string, 11)
	for i := range manyTags {
		manyTags[i] = "tag"
	}

	longTag := make([]byte, 51)
	for i := range longTag {
		longTag[i] = 'a'
	}

	tests := []struct {
		name string
		log  ConditionLog
	}{
		{"overall_vas -1", ConditionLog{OverallVAS: -1}},
		{"overall_vas 101", ConditionLog{OverallVAS: 101}},
		{"mood_vas out of range", ConditionLog{OverallVAS: 50, MoodVAS: intPtr(150)}},
		{"energy_vas out of range", ConditionLog{OverallVAS: 50, EnergyVAS: intPtr(-5)}},
		{"sleep_quality_vas out of range", ConditionLog{OverallVAS: 50, SleepQualityVAS: intPtr(101)}},
		{"stress_vas out of range", ConditionLog{OverallVAS: 50, StressVAS: intPtr(-1)}},
		{"legacy overall out of range", ConditionLog{OverallVAS: 50, Overall: 6}},
		{"legacy mental out of range", ConditionLog{OverallVAS: 50, Mental: intPtr(0)}},
		{"legacy physical out of range", ConditionLog{OverallVAS: 50, Physical: intPtr(6)}},
		{"legacy energy out of range", ConditionLog{OverallVAS: 50, Energy: intPtr(-1)}},
		{"note too long", ConditionLog{OverallVAS: 50, Note: string(longNote)}},
		{"too many tags", ConditionLog{OverallVAS: 50, Tags: manyTags}},
		{"tag too long", ConditionLog{OverallVAS: 50, Tags: []string{string(longTag)}}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if err := tt.log.Validate(); err == nil {
				t.Error("Validate() expected error, got nil")
			}
		})
	}
}

func TestVASToLegacyOverall(t *testing.T) {
	tests := []struct {
		vas  int
		want int
	}{
		{0, 1}, {10, 1}, {19, 1},
		{20, 2}, {39, 2},
		{40, 3}, {59, 3},
		{60, 4}, {79, 4},
		{80, 5}, {100, 5},
	}
	for _, tt := range tests {
		got := VASToLegacyOverall(tt.vas)
		if got != tt.want {
			t.Errorf("VASToLegacyOverall(%d) = %d, want %d", tt.vas, got, tt.want)
		}
	}
}
