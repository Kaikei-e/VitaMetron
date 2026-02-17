import type { PageServerLoad } from './$types';
import { apiFetch } from '$lib/server/api';
import type { ConditionLog, ConditionListResult } from '$lib/types/condition';
import type { DailySummary, HeartRateSample, SleepStageEntry, DataQuality, VRIScore } from '$lib/types/biometrics';

export const load: PageServerLoad = async () => {
	const today = new Date().toISOString().slice(0, 10);
	const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
	const sevenDaysAgo = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);

	const [condRes, bioRes, trendRes, yesterdayRes, rangeRes, todayHRRes, yesterdayHRRes, todaySleepRes, yesterdaySleepRes, qualityRes, vriRes, vriRangeRes] = await Promise.allSettled([
		apiFetch(`/api/conditions?limit=1&sort=logged_at&order=desc`),
		apiFetch(`/api/biometrics?date=${today}`),
		apiFetch(`/api/conditions?from=${sevenDaysAgo}&to=${today}&limit=7&sort=logged_at&order=asc`),
		apiFetch(`/api/biometrics?date=${yesterday}`),
		apiFetch(`/api/biometrics/range?from=${sevenDaysAgo}&to=${today}`),
		apiFetch(`/api/heartrate/intraday?date=${today}`),
		apiFetch(`/api/heartrate/intraday?date=${yesterday}`),
		apiFetch(`/api/sleep/stages?date=${today}`),
		apiFetch(`/api/sleep/stages?date=${yesterday}`),
		apiFetch(`/api/biometrics/quality?date=${today}`),
		apiFetch(`/api/vri?date=${today}`),
		apiFetch(`/api/vri/range?from=${sevenDaysAgo}&to=${today}`)
	]);

	let latestCondition: ConditionLog | null = null;
	if (condRes.status === 'fulfilled') {
		try {
			const data: ConditionListResult = await condRes.value.json();
			latestCondition = data.items?.[0] ?? null;
		} catch { /* ignore */ }
	}

	let todaySummary: DailySummary | null = null;
	if (bioRes.status === 'fulfilled') {
		try {
			todaySummary = await bioRes.value.json();
		} catch { /* ignore */ }
	}

	let recentConditions: ConditionLog[] = [];
	if (trendRes.status === 'fulfilled') {
		try {
			const data: ConditionListResult = await trendRes.value.json();
			recentConditions = data.items ?? [];
		} catch { /* ignore */ }
	}

	let yesterdaySummary: DailySummary | null = null;
	if (yesterdayRes.status === 'fulfilled') {
		try {
			yesterdaySummary = await yesterdayRes.value.json();
		} catch { /* ignore */ }
	}

	let weekSummaries: DailySummary[] = [];
	if (rangeRes.status === 'fulfilled') {
		try {
			weekSummaries = await rangeRes.value.json();
		} catch { /* ignore */ }
	}

	let todayHR: HeartRateSample[] = [];
	if (todayHRRes.status === 'fulfilled') {
		try {
			todayHR = await todayHRRes.value.json();
		} catch { /* ignore */ }
	}

	let yesterdayHR: HeartRateSample[] = [];
	if (yesterdayHRRes.status === 'fulfilled') {
		try {
			yesterdayHR = await yesterdayHRRes.value.json();
		} catch { /* ignore */ }
	}

	let todaySleep: SleepStageEntry[] = [];
	if (todaySleepRes.status === 'fulfilled') {
		try {
			todaySleep = await todaySleepRes.value.json();
		} catch { /* ignore */ }
	}

	let yesterdaySleep: SleepStageEntry[] = [];
	if (yesterdaySleepRes.status === 'fulfilled') {
		try {
			yesterdaySleep = await yesterdaySleepRes.value.json();
		} catch { /* ignore */ }
	}

	let dataQuality: DataQuality | null = null;
	if (qualityRes.status === 'fulfilled') {
		try {
			dataQuality = await qualityRes.value.json();
		} catch { /* ignore */ }
	}

	let todayVRI: VRIScore | null = null;
	if (vriRes.status === 'fulfilled') {
		try {
			todayVRI = await vriRes.value.json();
		} catch { /* ignore */ }
	}

	let weekVRI: VRIScore[] = [];
	if (vriRangeRes.status === 'fulfilled') {
		try {
			weekVRI = await vriRangeRes.value.json();
		} catch { /* ignore */ }
	}

	return {
		latestCondition,
		todaySummary,
		recentConditions,
		yesterdaySummary,
		weekSummaries,
		todayHR,
		yesterdayHR,
		todaySleep,
		yesterdaySleep,
		dataQuality,
		todayVRI,
		weekVRI
	};
};
