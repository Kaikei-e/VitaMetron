package healthconnect

import (
	"testing"
)

func TestPlausiblePick(t *testing.T) {
	isPositive := func(v int) bool { return v > 0 && v < 100 }

	tests := []struct {
		name    string
		apps    map[int]int
		wantVal int
		wantOK  bool
	}{
		{
			name:    "both plausible — prefer Fitbit",
			apps:    map[int]int{appFitbit: 50, appNothingX: 60},
			wantVal: 50,
			wantOK:  true,
		},
		{
			name:    "Fitbit implausible, NothingX plausible — pick NothingX",
			apps:    map[int]int{appFitbit: 999, appNothingX: 60},
			wantVal: 60,
			wantOK:  true,
		},
		{
			name:    "both implausible — fallback to Fitbit",
			apps:    map[int]int{appFitbit: -1, appNothingX: 200},
			wantVal: -1,
			wantOK:  true,
		},
		{
			name:    "Fitbit only plausible",
			apps:    map[int]int{appFitbit: 50},
			wantVal: 50,
			wantOK:  true,
		},
		{
			name:    "Fitbit only implausible — still returned (single source)",
			apps:    map[int]int{appFitbit: 999},
			wantVal: 999,
			wantOK:  true,
		},
		{
			name:    "NothingX only plausible",
			apps:    map[int]int{appNothingX: 60},
			wantVal: 60,
			wantOK:  true,
		},
		{
			name:    "NothingX only implausible — still returned (single source)",
			apps:    map[int]int{appNothingX: -5},
			wantVal: -5,
			wantOK:  true,
		},
		{
			name:    "empty map",
			apps:    map[int]int{},
			wantVal: 0,
			wantOK:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := plausiblePick(tt.apps, isPositive)
			if ok != tt.wantOK {
				t.Errorf("ok = %v, want %v", ok, tt.wantOK)
			}
			if got != tt.wantVal {
				t.Errorf("val = %v, want %v", got, tt.wantVal)
			}
		})
	}
}

func TestPlausiblePickFloat(t *testing.T) {
	inRange := func(v float64) bool { return v >= 30 && v <= 100 }

	tests := []struct {
		name    string
		apps    map[int]float64
		wantVal float64
		wantOK  bool
	}{
		{
			name:    "both plausible — prefer Fitbit",
			apps:    map[int]float64{appFitbit: 65.0, appNothingX: 70.0},
			wantVal: 65.0,
			wantOK:  true,
		},
		{
			name:    "Fitbit implausible, NothingX plausible — pick NothingX",
			apps:    map[int]float64{appFitbit: 5.0, appNothingX: 70.0},
			wantVal: 70.0,
			wantOK:  true,
		},
		{
			name:    "both implausible — fallback to Fitbit",
			apps:    map[int]float64{appFitbit: 5.0, appNothingX: 999.0},
			wantVal: 5.0,
			wantOK:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := plausiblePick(tt.apps, inRange)
			if ok != tt.wantOK {
				t.Errorf("ok = %v, want %v", ok, tt.wantOK)
			}
			if got != tt.wantVal {
				t.Errorf("val = %v, want %v", got, tt.wantVal)
			}
		})
	}
}

func TestPlausiblePickStruct(t *testing.T) {
	type hrData struct {
		avg float64
		max int
	}
	isPlausible := func(d hrData) bool { return d.avg >= 25 && d.avg <= 200 }

	tests := []struct {
		name    string
		apps    map[int]hrData
		wantAvg float64
		wantOK  bool
	}{
		{
			name:    "both plausible — prefer Fitbit",
			apps:    map[int]hrData{appFitbit: {avg: 72, max: 150}, appNothingX: {avg: 75, max: 140}},
			wantAvg: 72,
			wantOK:  true,
		},
		{
			name:    "Fitbit implausible avg, NothingX plausible — pick NothingX",
			apps:    map[int]hrData{appFitbit: {avg: 250, max: 300}, appNothingX: {avg: 75, max: 140}},
			wantAvg: 75,
			wantOK:  true,
		},
		{
			name:    "both implausible — fallback to Fitbit",
			apps:    map[int]hrData{appFitbit: {avg: 250, max: 300}, appNothingX: {avg: 999, max: 999}},
			wantAvg: 250,
			wantOK:  true,
		},
		{
			name:    "Fitbit only",
			apps:    map[int]hrData{appFitbit: {avg: 72, max: 150}},
			wantAvg: 72,
			wantOK:  true,
		},
		{
			name:    "NothingX only",
			apps:    map[int]hrData{appNothingX: {avg: 75, max: 140}},
			wantAvg: 75,
			wantOK:  true,
		},
		{
			name:    "empty",
			apps:    map[int]hrData{},
			wantAvg: 0,
			wantOK:  false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, ok := plausiblePick(tt.apps, isPlausible)
			if ok != tt.wantOK {
				t.Errorf("ok = %v, want %v", ok, tt.wantOK)
			}
			if got.avg != tt.wantAvg {
				t.Errorf("avg = %v, want %v", got.avg, tt.wantAvg)
			}
		})
	}
}
