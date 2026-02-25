/** Matches Go entity.DailySummary (PascalCase JSON, no json tags) */
export interface DailySummary {
	Date: string;
	Provider: string;

	// Heart rate
	RestingHR: number;
	AvgHR: number;
	MaxHR: number;

	// HRV
	HRVDailyRMSSD: number | null;
	HRVDeepRMSSD: number | null;

	// SpO2
	SpO2Avg: number | null;
	SpO2Min: number | null;
	SpO2Max: number | null;

	// Breathing rate
	BRFullSleep: number | null;
	BRDeepSleep: number | null;
	BRLightSleep: number | null;
	BRREMSleep: number | null;

	// Skin temperature
	SkinTempVariation: number | null;

	// Sleep
	SleepStart: string | null;
	SleepEnd: string | null;
	SleepDurationMin: number;
	SleepMinutesAsleep: number;
	SleepMinutesAwake: number;
	SleepOnsetLatency: number;
	SleepType: string;
	SleepDeepMin: number;
	SleepLightMin: number;
	SleepREMMin: number;
	SleepWakeMin: number;
	SleepIsMain: boolean;

	// Activity
	Steps: number;
	DistanceKM: number;
	Floors: number;
	CaloriesTotal: number;
	CaloriesActive: number;
	CaloriesBMR: number;
	ActiveZoneMin: number;
	MinutesSedentary: number;
	MinutesLightly: number;
	MinutesFairly: number;
	MinutesVery: number;

	// VO2 Max
	VO2Max: number | null;

	// Heart rate zones
	HRZoneOutMin: number;
	HRZoneFatMin: number;
	HRZoneCardioMin: number;
	HRZonePeakMin: number;

	SyncedAt: string;
}

export interface HeartRateSample {
	Time: string;
	BPM: number;
	Confidence: number;
}

export type SleepStage = 'deep' | 'light' | 'rem' | 'wake';

export interface SleepStageEntry {
	Time: string;
	Stage: SleepStage;
	Seconds: number;
	LogID: number;
}

export interface DataQuality {
	Date: string;
	WearTimeHours: number;
	HRSampleCount: number;
	CompletenessPct: number;
	MetricsPresent: string[];
	MetricsMissing: string[];
	PlausibilityPass: boolean;
	IsValidDay: boolean;
	BaselineDays: number;
	BaselineMaturity: string;
	ConfidenceScore: number;
	ConfidenceLevel: string;
	ComputedAt: string;
}

export interface VRIMetricContribution {
	metric: string;
	z_score: number;
	directed_z: number;
	direction: string;
	contribution: number;
}

export interface VRIScore {
	Date: string;
	VRIScore: number;
	VRIConfidence: number;
	ZLnRMSSD: number | null;
	ZRestingHR: number | null;
	ZSleepDuration: number | null;
	ZSRI: number | null;
	ZSpO2: number | null;
	ZDeepSleep: number | null;
	ZBR: number | null;
	SRIValue: number | null;
	SRIDaysUsed: number;
	BaselineWindowDays: number;
	BaselineMaturity: string;
	ContributingFactors: VRIMetricContribution[] | null;
	MetricsIncluded: string[];
	ComputedAt: string;
}

export interface AnomalyContribution {
	Feature: string;
	ShapValue: number;
	Direction: string;
	Description: string;
}

export interface AnomalyDetection {
	Date: string;
	AnomalyScore: number;
	NormalizedScore: number;
	IsAnomaly: boolean;
	QualityGate: string;
	QualityConfidence: number;
	QualityAdjustedScore: number;
	TopDrivers: AnomalyContribution[];
	Explanation: string;
	ModelVersion: string;
	ComputedAt: string;
}

export interface MetricComparison {
	label: string;
	today: number | null;
	yesterday: number | null;
	unit: string;
	delta: number | null;
	higherIsBetter: boolean;
}
