import { apiFetch, fetchJSON } from '$lib/server/api';
import { effectiveDateISO, effectiveDaysAgoISO } from '$lib/utils/date';
import type { ConditionLog, ConditionListResult } from '$lib/types/condition';
import type { DivergenceDetection, DivergenceModelStatus } from '$lib/types/insights';
import type { WHO5Assessment } from '$lib/types/who5';

const LIMIT = 20;

export interface ConditionsData {
	conditions: ConditionLog[];
	total: number;
	page: number;
	limit: number;
	divergenceStatus: Promise<DivergenceModelStatus | null>;
	divergenceRange: DivergenceDetection[];
	who5Latest: WHO5Assessment | null;
}

export async function loadConditions(url: URL): Promise<ConditionsData> {
	const page = Math.max(1, Number(url.searchParams.get('page')) || 1);
	const offset = (page - 1) * LIMIT;

	const today = effectiveDateISO();
	const thirtyDaysAgo = effectiveDaysAgoISO(30);

	// Fast (DB direct) — await these
	const [conditionsResult, divergenceRange, who5Latest] = await Promise.all([
		fetchJSON<ConditionListResult>(
			`/api/conditions?limit=${LIMIT}&offset=${offset}&sort=logged_at&order=desc`,
			{ items: [], total: 0 }
		),
		fetchJSON<DivergenceDetection[]>(
			`/api/divergence/range?from=${thirtyDaysAgo}&to=${today}`,
			[]
		),
		fetchJSON<WHO5Assessment | null>('/api/who5/latest', null)
	]);

	// Slow (ML dependent) — don't await, stream to client
	const divergenceStatus = apiFetch('/api/divergence/status')
		.then((res) => res.json() as Promise<DivergenceModelStatus>)
		.catch(() => null);

	return {
		conditions: conditionsResult.items ?? [],
		total: conditionsResult.total ?? 0,
		page,
		limit: LIMIT,
		divergenceStatus,
		divergenceRange,
		who5Latest
	};
}
