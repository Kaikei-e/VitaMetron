import type { PageServerLoad } from './$types';
import { loadDashboard } from '$lib/server/services/dashboard';

export const load: PageServerLoad = async () => loadDashboard();
