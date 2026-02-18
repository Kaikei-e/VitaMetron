import { apiFetch } from '$lib/api';
import type { CreateWHO5Request } from '$lib/types/who5';

export async function createWHO5(body: CreateWHO5Request): Promise<void> {
	await apiFetch('/api/who5', {
		method: 'POST',
		body: JSON.stringify(body)
	});
}
