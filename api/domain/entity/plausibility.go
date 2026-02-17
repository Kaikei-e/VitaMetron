package entity

const (
	RestingHRMin     float32 = 30
	RestingHRMax     float32 = 100
	RMSSDMin         float32 = 5
	RMSSDMax         float32 = 300
	SpO2Min          float32 = 70
	SpO2Max          float32 = 100
	SkinTempDeltaMin float32 = -5
	SkinTempDeltaMax float32 = 5
	BRMin            float32 = 4
	BRMax            float32 = 40
)

// allMetrics defines the full set of metrics we track for completeness.
var allMetrics = []string{"hr", "hrv", "spo2", "sleep", "activity", "br", "temp"}

// CheckPlausibility checks whether each metric in the DailySummary falls
// within a physiologically plausible range. Zero-value fields are treated
// as "missing" rather than failing plausibility.
func CheckPlausibility(s *DailySummary) map[string]string {
	flags := make(map[string]string)

	// Resting HR
	if s.RestingHR == 0 {
		flags["resting_hr"] = "missing"
	} else {
		hr := float32(s.RestingHR)
		switch {
		case hr < RestingHRMin:
			flags["resting_hr"] = "fail_low"
		case hr > RestingHRMax:
			flags["resting_hr"] = "fail_high"
		default:
			flags["resting_hr"] = "pass"
		}
	}

	// HRV RMSSD
	if s.HRVDailyRMSSD == 0 {
		flags["hrv_rmssd"] = "missing"
	} else {
		switch {
		case s.HRVDailyRMSSD < RMSSDMin:
			flags["hrv_rmssd"] = "fail_low"
		case s.HRVDailyRMSSD > RMSSDMax:
			flags["hrv_rmssd"] = "fail_high"
		default:
			flags["hrv_rmssd"] = "pass"
		}
	}

	// SpO2
	if s.SpO2Avg == 0 {
		flags["spo2"] = "missing"
	} else {
		switch {
		case s.SpO2Avg < SpO2Min:
			flags["spo2"] = "fail_low"
		case s.SpO2Avg > SpO2Max:
			flags["spo2"] = "fail_high"
		default:
			flags["spo2"] = "pass"
		}
	}

	// Skin temperature variation
	if s.SkinTempVariation == 0 {
		flags["skin_temp"] = "missing"
	} else {
		switch {
		case s.SkinTempVariation < SkinTempDeltaMin:
			flags["skin_temp"] = "fail_low"
		case s.SkinTempVariation > SkinTempDeltaMax:
			flags["skin_temp"] = "fail_high"
		default:
			flags["skin_temp"] = "pass"
		}
	}

	// Breathing rate (full sleep)
	if s.BRFullSleep == 0 {
		flags["br"] = "missing"
	} else {
		switch {
		case s.BRFullSleep < BRMin:
			flags["br"] = "fail_low"
		case s.BRFullSleep > BRMax:
			flags["br"] = "fail_high"
		default:
			flags["br"] = "pass"
		}
	}

	return flags
}

// CheckMetricCompleteness returns which metrics are present, which are missing,
// and the overall completeness percentage.
func CheckMetricCompleteness(s *DailySummary) (present []string, missing []string, pct float32) {
	checks := map[string]bool{
		"hr":       s.RestingHR != 0,
		"hrv":      s.HRVDailyRMSSD != 0,
		"spo2":     s.SpO2Avg != 0,
		"sleep":    s.SleepDurationMin != 0,
		"activity": s.Steps != 0,
		"br":       s.BRFullSleep != 0,
		"temp":     s.SkinTempVariation != 0,
	}

	for _, m := range allMetrics {
		if checks[m] {
			present = append(present, m)
		} else {
			missing = append(missing, m)
		}
	}

	if len(allMetrics) > 0 {
		pct = float32(len(present)) / float32(len(allMetrics))
	}
	return present, missing, pct
}
