/** Matches Go entity.ConditionLog (PascalCase JSON, no json tags) */
export interface ConditionLog {
	ID: number;
	LoggedAt: string;
	// Legacy (backward compat)
	Overall: number;
	Mental: number | null;
	Physical: number | null;
	Energy: number | null;
	// VAS 0-100 (primary)
	OverallVAS: number;
	MoodVAS: number | null;
	EnergyVAS: number | null;
	SleepQualityVAS: number | null;
	StressVAS: number | null;
	Note: string;
	Tags: string[];
	CreatedAt: string;
}

/** Matches Go handler.createConditionRequest */
export interface CreateConditionRequest {
	wellbeing: number; // 0-100, required
	mood?: number; // 0-100
	energy?: number; // 0-100
	sleep_quality?: number; // 0-100
	stress?: number; // 0-100
	note?: string;
	tags?: string[];
	logged_at?: string;
}

/** Matches Go entity.ConditionListResult (lowercase JSON via json tags) */
export interface ConditionListResult {
	items: ConditionLog[];
	total: number;
}

/** Matches Go entity.ConditionSummary (snake_case JSON via json tags) */
export interface ConditionSummary {
	total_count: number;
	overall_avg: number;
	overall_min: number;
	overall_max: number;
	mental_avg: number;
	mental_min: number;
	mental_max: number;
	physical_avg: number;
	physical_min: number;
	physical_max: number;
	energy_avg: number;
	energy_min: number;
	energy_max: number;
	overall_vas_avg: number;
	overall_vas_min: number;
	overall_vas_max: number;
	mood_vas_avg: number;
	mood_vas_min: number;
	mood_vas_max: number;
	energy_vas_avg: number;
	energy_vas_min: number;
	energy_vas_max: number;
	sleep_quality_vas_avg: number;
	sleep_quality_vas_min: number;
	sleep_quality_vas_max: number;
	stress_vas_avg: number;
	stress_vas_min: number;
	stress_vas_max: number;
}

/** Matches Go entity.TagCount (lowercase JSON via json tags) */
export interface TagCount {
	tag: string;
	count: number;
}
