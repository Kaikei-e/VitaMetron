package entity

import "time"

type DataQuality struct {
	Date              time.Time
	WearTimeHours     float32
	HRSampleCount     int
	CompletenessPct   float32
	MetricsPresent    []string
	MetricsMissing    []string
	PlausibilityFlags map[string]string // "pass" | "fail_low" | "fail_high" | "missing"
	PlausibilityPass  bool
	IsValidDay        bool
	BaselineDays      int
	BaselineMaturity  string // "cold" | "warming" | "mature"
	ConfidenceScore   float32
	ConfidenceLevel   string // "low" | "medium" | "high"
	ComputedAt        time.Time
}
