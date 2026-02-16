package fitbit

import (
	"math"
	"testing"
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

func float64Ptr(v float64) *float64 { return &v }
