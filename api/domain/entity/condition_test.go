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
		{"overall 1", ConditionLog{Overall: 1, LoggedAt: time.Now()}},
		{"overall 5", ConditionLog{Overall: 5, LoggedAt: time.Now()}},
		{"overall 3 with optionals", ConditionLog{
			Overall:  3,
			Mental:   intPtr(2),
			Physical: intPtr(4),
			Energy:   intPtr(5),
			LoggedAt: time.Now(),
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
	tests := []struct {
		name string
		log  ConditionLog
	}{
		{"overall 0", ConditionLog{Overall: 0}},
		{"overall 6", ConditionLog{Overall: 6}},
		{"mental out of range", ConditionLog{Overall: 3, Mental: intPtr(0)}},
		{"physical out of range", ConditionLog{Overall: 3, Physical: intPtr(6)}},
		{"energy out of range", ConditionLog{Overall: 3, Energy: intPtr(-1)}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if err := tt.log.Validate(); err == nil {
				t.Error("Validate() expected error, got nil")
			}
		})
	}
}
