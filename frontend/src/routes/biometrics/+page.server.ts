import type { PageServerLoad } from './$types';
import { apiFetch } from '$lib/server/api';
import type { DailySummary } from '$lib/types/biometrics';

export const load: PageServerLoad = async ({ url }) => {
	const selectedDate = url.searchParams.get('date') || new Date().toISOString().slice(0, 10);

	let dailySummary: DailySummary | null = null;

	try {
		const res = await apiFetch(`/api/biometrics?date=${selectedDate}`);
		dailySummary = await res.json();
	} catch {
		/* no data for this date */
	}

	return {
		dailySummary,
		selectedDate
	};
};
