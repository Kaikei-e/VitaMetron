import type { PageServerLoad } from './$types';
import { loadConditions } from '$lib/server/services/conditions';

export const load: PageServerLoad = async ({ url }) => loadConditions(url);
