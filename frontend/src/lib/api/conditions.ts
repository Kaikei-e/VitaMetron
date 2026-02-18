import { apiFetch } from '$lib/api';
import type { CreateConditionRequest, TagCount } from '$lib/types/condition';

export async function createCondition(body: CreateConditionRequest): Promise<void> {
	await apiFetch('/api/conditions', {
		method: 'POST',
		body: JSON.stringify(body)
	});
}

export async function deleteCondition(id: number): Promise<void> {
	await apiFetch(`/api/conditions/${id}`, { method: 'DELETE' });
}

export async function fetchTags(): Promise<string[]> {
	const res = await apiFetch('/api/conditions/tags');
	const data: TagCount[] = await res.json();
	return data.map((t) => t.tag);
}
