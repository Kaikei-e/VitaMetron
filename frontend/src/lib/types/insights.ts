/** Matches Go entity.ConditionPrediction (PascalCase JSON, no json tags) */
export interface ConditionPrediction {
	TargetDate: string;
	PredictedScore: number;
	Confidence: number;
	ContributingFactors: ContributingFactor[];
	RiskSignals: string[];
	PredictedAt: string;
}

/** Matches Go application.InsightsResult (PascalCase JSON, no json tags) */
export interface InsightsResult {
	Prediction: ConditionPrediction | null;
	Risks: string[];
}

export interface ContributingFactor {
	feature: string;
	importance: number;
	direction: string;
	value: number;
	baseline: number;
}

/** Matches Go entity.HRVPrediction */
export interface HRVPrediction {
	Date: string;
	TargetDate: string;
	PredictedZScore: number;
	PredictedDirection: string;
	Confidence: number;
	TopDrivers: HRVFeatureContribution[];
	ModelVersion: string;
	ComputedAt: string;
}

export interface HRVFeatureContribution {
	feature: string;
	shap_value: number;
	direction: string;
}

/** Matches Go entity.HRVModelStatus */
export interface HRVModelStatus {
	IsReady: boolean;
	ModelVersion: string;
	TrainingDays: number;
	CVMetrics: Record<string, number>;
	StableFeatures: string[];
}

/** Matches Go entity.WeeklyInsight */
export interface WeeklyInsight {
	WeekStart: string;
	WeekEnd: string;
	AvgScore: number | null;
	Trend: string;
	TopFactors: string[];
	RiskSummary: string[];
}

/** Matches Go entity.DivergenceDetection */
export interface DivergenceDetection {
	Date: string;
	ConditionLogID: number;
	ActualScore: number;
	PredictedScore: number;
	Residual: number;
	CuSumPositive: number;
	CuSumNegative: number;
	CuSumAlert: boolean;
	DivergenceType: string;
	Confidence: number;
	TopDrivers: DivergenceContribution[];
	Explanation: string;
	ModelVersion: string;
}

export interface DivergenceContribution {
	feature: string;
	coefficient: number;
	feature_value: number;
	contribution: number;
	direction: string;
}

/** Matches Go entity.DivergenceModelStatus */
export interface DivergenceModelStatus {
	IsReady: boolean;
	ModelVersion: string;
	TrainingPairs: number;
	MinPairsNeeded: number;
	R2Score: number | null;
	MAE: number | null;
	Phase: string;
	Message: string;
}
