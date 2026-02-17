/** Matches Go entity.ConditionLog (PascalCase JSON, no json tags) */
export interface ConditionLog {
	ID: number;
	LoggedAt: string;
	Overall: number;
	Mental: number | null;
	Physical: number | null;
	Energy: number | null;
	OverallVAS: number | null;
	Note: string;
	Tags: string[];
	CreatedAt: string;
}

/** Matches Go handler.createConditionRequest (camelCase JSON via json tags) */
export interface CreateConditionRequest {
	overall: number;
	mental?: number;
	physical?: number;
	energy?: number;
	overall_vas?: number;
	note?: string;
	tags?: string[];
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
}

/** Matches Go entity.TagCount (lowercase JSON via json tags) */
export interface TagCount {
	tag: string;
	count: number;
}
