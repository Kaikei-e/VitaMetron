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

export interface CircadianMetricContribution {
	metric: string;
	z_score: number;
	directed_z: number;
	direction: string;
	contribution: number;
}

export interface CircadianCosinor {
	CosinorMesor: number;
	CosinorAmplitude: number;
	CosinorAcrophaseHour: number;
}

export interface CircadianNPAR {
	NPARIS: number;
	NPARIV: number;
	NPARRA: number;
	NPARM10: number;
	NPARM10Start: number;
	NPARL5: number;
	NPARL5Start: number;
}

export interface CircadianSleepTiming {
	SleepMidpointHour: number;
	SleepMidpointVarMin: number;
	SocialJetlagMin: number;
}

export interface CircadianNocturnalDip {
	NocturnalDipPct: number;
	DaytimeMeanHR: number;
	NighttimeMeanHR: number;
}

export interface CircadianScore {
	Date: string;
	CHSScore: number;
	CHSConfidence: number;
	CosinorMesor: number | null;
	CosinorAmplitude: number | null;
	CosinorAcrophaseHour: number | null;
	NPARIS: number | null;
	NPARIV: number | null;
	NPARRA: number | null;
	NPARM10: number | null;
	NPARM10Start: number | null;
	NPARL5: number | null;
	NPARL5Start: number | null;
	SleepMidpointHour: number | null;
	SleepMidpointVarMin: number | null;
	SocialJetlagMin: number | null;
	NocturnalDipPct: number | null;
	DaytimeMeanHR: number | null;
	NighttimeMeanHR: number | null;
	ZRhythmStrength: number | null;
	ZRhythmStability: number | null;
	ZRhythmFragmentation: number | null;
	ZSleepRegularity: number | null;
	ZPhaseAlignment: number | null;
	SRIValue: number | null;
	BaselineWindowDays: number;
	BaselineMaturity: string;
	ContributingFactors: CircadianMetricContribution[] | null;
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
