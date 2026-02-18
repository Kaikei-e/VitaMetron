import { apiFetch } from '$lib/api';
import type { DailyAdvice } from '$lib/types/advice';

export async function regenerateAdvice(date: string): Promise<DailyAdvice> {
	const res = await apiFetch(`/api/advice/regenerate?date=${date}`, { method: 'POST' });
	return (await res.json()) as DailyAdvice;
}
