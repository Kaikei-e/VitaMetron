import { apiFetch, fetchJSON } from '$lib/server/api';
import { todayISO, daysAgoISO } from '$lib/utils/date';
import type {
	InsightsResult,
	HRVPrediction,
	HRVModelStatus,
	WeeklyInsight
} from '$lib/types/insights';
import type { AnomalyDetection } from '$lib/types/biometrics';

export interface InsightsData {
	insights: Promise<InsightsResult | null>;
	hrvPrediction: Promise<HRVPrediction | null>;
	hrvStatus: Promise<HRVModelStatus | null>;
	anomaly: AnomalyDetection | null;
	weeklyInsight: Promise<WeeklyInsight | null>;
	anomalyRange: AnomalyDetection[];
}

export async function loadInsights(): Promise<InsightsData> {
	const today = todayISO();
	const weekAgo = daysAgoISO(7);

	// Fast (DB / cached) — await these
	const [anomaly, anomalyRange] = await Promise.all([
		fetchJSON<AnomalyDetection | null>(`/api/anomaly?date=${today}`, null),
		fetchJSON<AnomalyDetection[]>(`/api/anomaly/range?from=${weekAgo}&to=${today}`, [])
	]);

	// Slow (ML dependent) — don't await, stream to client
	const insights = apiFetch(`/api/insights?date=${today}`)
		.then((r) => r.json() as Promise<InsightsResult>)
		.catch(() => null);
	const hrvPrediction = apiFetch(`/api/hrv/predict?date=${today}`)
		.then((r) => r.json() as Promise<HRVPrediction>)
		.catch(() => null);
	const hrvStatus = apiFetch(`/api/hrv/status`)
		.then((r) => r.json() as Promise<HRVModelStatus>)
		.catch(() => null);
	const weeklyInsight = apiFetch(`/api/insights/weekly?date=${today}`)
		.then((r) => r.json() as Promise<WeeklyInsight>)
		.catch(() => null);

	return {
		insights,
		hrvPrediction,
		hrvStatus,
		anomaly,
		weeklyInsight,
		anomalyRange
	};
}
