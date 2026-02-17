import type { PageServerLoad } from './$types';
import { apiFetch } from '$lib/server/api';
import type { ConditionListResult } from '$lib/types/condition';
import type { DivergenceDetection, DivergenceModelStatus } from '$lib/types/insights';

const LIMIT = 20;

export const load: PageServerLoad = async ({ url }) => {
	const page = Math.max(1, Number(url.searchParams.get('page')) || 1);
	const offset = (page - 1) * LIMIT;

	const today = new Date().toISOString().slice(0, 10);
	const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);

	// Fast (DB direct) — await these
	const [conditionsResult, divergenceRangeResult] = await Promise.allSettled([
		apiFetch(
			`/api/conditions?limit=${LIMIT}&offset=${offset}&sort=logged_at&order=desc`
		).then((res) => res.json() as Promise<ConditionListResult>),
		apiFetch(`/api/divergence/range?from=${thirtyDaysAgo}&to=${today}`).then(
			(res) => res.json() as Promise<DivergenceDetection[]>
		)
	]);

	// Slow (ML dependent) — don't await, stream to client
	const divergenceStatus = apiFetch('/api/divergence/status')
		.then((res) => res.json() as Promise<DivergenceModelStatus>)
		.catch(() => null);

	return {
		conditions:
			conditionsResult.status === 'fulfilled' ? (conditionsResult.value.items ?? []) : [],
		total: conditionsResult.status === 'fulfilled' ? (conditionsResult.value.total ?? 0) : 0,
		page,
		limit: LIMIT,
		divergenceStatus,
		divergenceRange:
			divergenceRangeResult.status === 'fulfilled' ? divergenceRangeResult.value : []
	};
};
