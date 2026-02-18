export interface DailyAdvice {
	Date: string;
	AdviceText: string;
	ModelName: string;
	GenerationMs: number | null;
	Cached: boolean;
	GeneratedAt: string;
}
