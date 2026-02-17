import type { PageServerLoad } from './$types';
import { apiFetch } from '$lib/server/api';
import type {
	InsightsResult,
	HRVPrediction,
	HRVModelStatus,
	WeeklyInsight
} from '$lib/types/insights';
import type { AnomalyDetection } from '$lib/types/biometrics';

export const load: PageServerLoad = async () => {
	const today = new Date().toISOString().slice(0, 10);
	const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);

	// Fast (DB / cached) — await these
	const [anomalyRes, anomalyRangeRes] = await Promise.allSettled([
		apiFetch(`/api/anomaly?date=${today}`),
		apiFetch(`/api/anomaly/range?from=${weekAgo}&to=${today}`)
	]);

	let anomaly: AnomalyDetection | null = null;
	let anomalyRange: AnomalyDetection[] = [];

	if (anomalyRes.status === 'fulfilled') {
		try {
			anomaly = await anomalyRes.value.json();
		} catch {
			/* no data */
		}
	}
	if (anomalyRangeRes.status === 'fulfilled') {
		try {
			anomalyRange = await anomalyRangeRes.value.json();
		} catch {
			/* no data */
		}
	}

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
};
