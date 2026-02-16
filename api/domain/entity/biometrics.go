package entity

type HRVSummary struct {
	DailyRMSSD *float64
	DeepRMSSD  *float64
}

type SpO2Summary struct {
	Avg *float64
	Min *float64
	Max *float64
}

type BreathingRateSummary struct {
	FullSleep  *float64
	DeepSleep  *float64
	LightSleep *float64
	RemSleep   *float64
}

type SkinTemperature struct {
	Variation *float64
}

type VO2Max struct {
	Value *float64
}
