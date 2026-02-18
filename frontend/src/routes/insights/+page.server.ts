import type { PageServerLoad } from './$types';
import { loadInsights } from '$lib/server/services/insights';

export const load: PageServerLoad = async () => loadInsights();
