import { apiFetch } from '$lib/api';

export async function syncNow(date?: string): Promise<void> {
	const url = date ? `/api/sync?date=${date}` : '/api/sync';
	const res = await apiFetch(url, { method: 'POST' });
	if (!res.ok) throw new Error('Sync failed');
}

export async function getFitbitAuthUrl(): Promise<string> {
	const res = await apiFetch('/api/auth/fitbit');
	const { url }: { url: string } = await res.json();
	return url;
}

export async function disconnectFitbit(): Promise<void> {
	await apiFetch('/api/auth/fitbit', { method: 'DELETE' });
}
