import { apiFetch, fetchJSON } from '$lib/server/api';
import { effectiveDateISO, effectiveDaysAgoISO, isOvernightHours } from '$lib/utils/date';
import type { ConditionLog, ConditionListResult } from '$lib/types/condition';
import type {
	DailySummary,
	HeartRateSample,
	SleepStageEntry,
	DataQuality,
	VRIScore
} from '$lib/types/biometrics';
import type { DailyAdvice } from '$lib/types/advice';

export interface DashboardData {
	latestCondition: ConditionLog | null;
	todaySummary: DailySummary | null;
	recentConditions: ConditionLog[];
	yesterdaySummary: DailySummary | null;
	weekSummaries: DailySummary[];
	todayHR: HeartRateSample[];
	yesterdayHR: HeartRateSample[];
	todaySleep: SleepStageEntry[];
	yesterdaySleep: SleepStageEntry[];
	dataQuality: DataQuality | null;
	todayVRI: VRIScore | null;
	weekVRI: VRIScore[];
	monthSummaries: DailySummary[];
	monthVRI: VRIScore[];
	monthConditions: ConditionLog[];
	todayAdvice: Promise<DailyAdvice | null>;
	isOvernightMode: boolean;
	effectiveDate: string;
}

export async function loadDashboard(): Promise<DashboardData> {
	const overnight = isOvernightHours();
	const today = effectiveDateISO();
	const yesterday = effectiveDaysAgoISO(1);
	const sevenDaysAgo = effectiveDaysAgoISO(7);
	const thirtyDaysAgo = effectiveDaysAgoISO(30);

	// Start advice fetch early — don't await (LLM generation can be slow, 120s timeout)
	const todayAdvice = fetchJSON<DailyAdvice | null>(`/api/advice?date=${today}`, null, 120_000);

	const [
		condRes,
		todaySummary,
		recentCondRes,
		yesterdaySummary,
		weekSummaries,
		todayHR,
		yesterdayHR,
		todaySleep,
		yesterdaySleep,
		dataQuality,
		todayVRI,
		weekVRI,
		monthSummaries,
		monthVRI,
		monthCondRes
	] = await Promise.all([
		fetchJSON<ConditionListResult>(
			`/api/conditions?limit=1&sort=logged_at&order=desc`,
			{ items: [], total: 0 }
		),
		fetchJSON<DailySummary | null>(`/api/biometrics?date=${today}`, null),
		fetchJSON<ConditionListResult>(
			`/api/conditions?from=${sevenDaysAgo}&to=${today}&limit=7&sort=logged_at&order=asc`,
			{ items: [], total: 0 }
		),
		fetchJSON<DailySummary | null>(`/api/biometrics?date=${yesterday}`, null),
		fetchJSON<DailySummary[]>(`/api/biometrics/range?from=${sevenDaysAgo}&to=${today}`, []),
		fetchJSON<HeartRateSample[]>(`/api/heartrate/intraday?date=${today}`, []),
		fetchJSON<HeartRateSample[]>(`/api/heartrate/intraday?date=${yesterday}`, []),
		fetchJSON<SleepStageEntry[]>(`/api/sleep/stages?date=${today}`, []),
		fetchJSON<SleepStageEntry[]>(`/api/sleep/stages?date=${yesterday}`, []),
		fetchJSON<DataQuality | null>(`/api/biometrics/quality?date=${today}`, null),
		fetchJSON<VRIScore | null>(`/api/vri?date=${today}`, null),
		fetchJSON<VRIScore[]>(`/api/vri/range?from=${sevenDaysAgo}&to=${today}`, []),
		fetchJSON<DailySummary[]>(`/api/biometrics/range?from=${thirtyDaysAgo}&to=${today}`, []),
		fetchJSON<VRIScore[]>(`/api/vri/range?from=${thirtyDaysAgo}&to=${today}`, []),
		fetchJSON<ConditionListResult>(
			`/api/conditions?from=${thirtyDaysAgo}&to=${today}&limit=30&sort=logged_at&order=asc`,
			{ items: [], total: 0 }
		)
	]);

	return {
		latestCondition: condRes.items?.[0] ?? null,
		todaySummary,
		recentConditions: recentCondRes.items ?? [],
		yesterdaySummary,
		weekSummaries,
		todayHR,
		yesterdayHR,
		todaySleep,
		yesterdaySleep,
		dataQuality,
		todayVRI,
		weekVRI,
		monthSummaries,
		monthVRI,
		monthConditions: monthCondRes.items ?? [],
		todayAdvice,
		isOvernightMode: overnight,
		effectiveDate: today
	};
}
