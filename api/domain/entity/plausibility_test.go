package entity

import "testing"

func TestCheckPlausibility_NormalValues(t *testing.T) {
	s := &DailySummary{
		RestingHR:         62,
		HRVDailyRMSSD:    45.0,
		SpO2Avg:          97.0,
		SkinTempVariation: 0.5,
		BRFullSleep:       15.0,
	}
	flags := CheckPlausibility(s)

	for metric, status := range flags {
		if status != "pass" {
			t.Errorf("metric %s: got %s, want pass", metric, status)
		}
	}
}

func TestCheckPlausibility_OutOfRangeHR(t *testing.T) {
	tests := []struct {
		name   string
		hr     int
		expect string
	}{
		{"too_low", 25, "fail_low"},
		{"too_high", 110, "fail_high"},
		{"boundary_low", 30, "pass"},
		{"boundary_high", 100, "pass"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := &DailySummary{RestingHR: tt.hr}
			flags := CheckPlausibility(s)
			if flags["resting_hr"] != tt.expect {
				t.Errorf("resting_hr = %s, want %s", flags["resting_hr"], tt.expect)
			}
		})
	}
}

func TestCheckPlausibility_OutOfRangeRMSSD(t *testing.T) {
	tests := []struct {
		name   string
		rmssd  float32
		expect string
	}{
		{"too_low", 3.0, "fail_low"},
		{"too_high", 350.0, "fail_high"},
		{"boundary_low", 5.0, "pass"},
		{"boundary_high", 300.0, "pass"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := &DailySummary{HRVDailyRMSSD: tt.rmssd}
			flags := CheckPlausibility(s)
			if flags["hrv_rmssd"] != tt.expect {
				t.Errorf("hrv_rmssd = %s, want %s", flags["hrv_rmssd"], tt.expect)
			}
		})
	}
}

func TestCheckPlausibility_MissingValues(t *testing.T) {
	s := &DailySummary{}
	flags := CheckPlausibility(s)

	expected := []string{"resting_hr", "hrv_rmssd", "spo2", "skin_temp", "br"}
	for _, metric := range expected {
		if flags[metric] != "missing" {
			t.Errorf("metric %s: got %s, want missing", metric, flags[metric])
		}
	}
}

func TestCheckPlausibility_SpO2Ranges(t *testing.T) {
	tests := []struct {
		name   string
		spo2   float32
		expect string
	}{
		{"too_low", 65.0, "fail_low"},
		{"normal", 96.0, "pass"},
		{"boundary_high", 100.0, "pass"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := &DailySummary{SpO2Avg: tt.spo2}
			flags := CheckPlausibility(s)
			if flags["spo2"] != tt.expect {
				t.Errorf("spo2 = %s, want %s", flags["spo2"], tt.expect)
			}
		})
	}
}

func TestCheckPlausibility_BRRanges(t *testing.T) {
	tests := []struct {
		name   string
		br     float32
		expect string
	}{
		{"too_low", 3.0, "fail_low"},
		{"too_high", 45.0, "fail_high"},
		{"normal", 15.0, "pass"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := &DailySummary{BRFullSleep: tt.br}
			flags := CheckPlausibility(s)
			if flags["br"] != tt.expect {
				t.Errorf("br = %s, want %s", flags["br"], tt.expect)
			}
		})
	}
}

func TestCheckMetricCompleteness_AllPresent(t *testing.T) {
	s := &DailySummary{
		RestingHR:         62,
		HRVDailyRMSSD:    45.0,
		SpO2Avg:          97.0,
		SleepDurationMin:  420,
		Steps:            8000,
		BRFullSleep:       15.0,
		SkinTempVariation: 0.5,
	}
	present, missing, pct := CheckMetricCompleteness(s)
	if len(present) != 7 {
		t.Errorf("present count = %d, want 7", len(present))
	}
	if len(missing) != 0 {
		t.Errorf("missing count = %d, want 0", len(missing))
	}
	if pct != 1.0 {
		t.Errorf("pct = %f, want 1.0", pct)
	}
}

func TestCheckMetricCompleteness_SomeMissing(t *testing.T) {
	s := &DailySummary{
		RestingHR:        62,
		HRVDailyRMSSD:   45.0,
		SleepDurationMin: 420,
		Steps:            8000,
	}
	present, missing, pct := CheckMetricCompleteness(s)
	if len(present) != 4 {
		t.Errorf("present count = %d, want 4", len(present))
	}
	if len(missing) != 3 {
		t.Errorf("missing count = %d, want 3", len(missing))
	}
	expectedPct := float32(4.0 / 7.0)
	if pct < expectedPct-0.01 || pct > expectedPct+0.01 {
		t.Errorf("pct = %f, want ~%f", pct, expectedPct)
	}
}

func TestCheckMetricCompleteness_NonePresent(t *testing.T) {
	s := &DailySummary{}
	present, missing, pct := CheckMetricCompleteness(s)
	if len(present) != 0 {
		t.Errorf("present count = %d, want 0", len(present))
	}
	if len(missing) != 7 {
		t.Errorf("missing count = %d, want 7", len(missing))
	}
	if pct != 0.0 {
		t.Errorf("pct = %f, want 0.0", pct)
	}
}
