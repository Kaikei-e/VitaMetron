import type { PageServerLoad } from './$types';
import { apiFetch } from '$lib/server/api';

export const load: PageServerLoad = async ({ url }) => {
	let fitbitConnected = false;

	try {
		const res = await apiFetch('/api/auth/fitbit/status');
		const data: { status: string } = await res.json();
		fitbitConnected = data.status === 'connected';
	} catch {
		fitbitConnected = false;
	}

	return {
		fitbitConnected,
		fitbitResult: url.searchParams.get('fitbit')
	};
};
