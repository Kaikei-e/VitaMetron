<script lang="ts">
	import ConditionCard from '$lib/components/dashboard/ConditionCard.svelte';
	import MetricTile from '$lib/components/dashboard/MetricTile.svelte';
	import TrendChart from '$lib/components/dashboard/TrendChart.svelte';
	import DashboardTabs from '$lib/components/dashboard/DashboardTabs.svelte';
	import ComparisonTile from '$lib/components/dashboard/ComparisonTile.svelte';
	import WeeklyTrendCard from '$lib/components/dashboard/WeeklyTrendCard.svelte';
	import IntradayHRChart from '$lib/components/dashboard/IntradayHRChart.svelte';
	import SleepStageTimeline from '$lib/components/dashboard/SleepStageTimeline.svelte';
	import VRICard from '$lib/components/dashboard/VRICard.svelte';
	import VRITrendChart from '$lib/components/dashboard/VRITrendChart.svelte';
	import DailyAdviceCard from '$lib/components/dashboard/DailyAdviceCard.svelte';
	import { formatDateTime } from '$lib/utils/date';
	import type { MetricComparison } from '$lib/types/biometrics';

	let { data } = $props();

	function lastUpdated(): Date | null {
		const candidates = [
			data.todaySummary?.SyncedAt,
			data.todayVRI?.ComputedAt,
			data.dataQuality?.ComputedAt,
			data.latestCondition?.LoggedAt
		]
			.filter((v): v is string => v != null)
			.map((v) => new Date(v));
		if (candidates.length === 0) return null;
		return candidates.reduce((a, b) => (a > b ? a : b));
	}

	function delta(today: number | null, yesterday: number | null): number | null {
		if (today == null || yesterday == null) return null;
		return today - yesterday;
	}

	let comparisons = $derived<MetricComparison[]>([
		{
			label: 'Resting HR',
			today: data.todaySummary?.RestingHR ?? null,
			yesterday: data.yesterdaySummary?.RestingHR ?? null,
			unit: 'bpm',
			delta: delta(data.todaySummary?.RestingHR ?? null, data.yesterdaySummary?.RestingHR ?? null),
			higherIsBetter: false
		},
		{
			label: 'HRV Daily',
			today: data.todaySummary?.HRVDailyRMSSD ?? null,
			yesterday: data.yesterdaySummary?.HRVDailyRMSSD ?? null,
			unit: 'ms',
			delta: delta(data.todaySummary?.HRVDailyRMSSD ?? null, data.yesterdaySummary?.HRVDailyRMSSD ?? null),
			higherIsBetter: true
		},
		{
			label: 'SpO2',
			today: data.todaySummary?.SpO2Avg ?? null,
			yesterday: data.yesterdaySummary?.SpO2Avg ?? null,
			unit: '%',
			delta: delta(data.todaySummary?.SpO2Avg ?? null, data.yesterdaySummary?.SpO2Avg ?? null),
			higherIsBetter: true
		},
		{
			label: 'Sleep',
			today: data.todaySummary ? data.todaySummary.SleepDurationMin / 60 : null,
			yesterday: data.yesterdaySummary ? data.yesterdaySummary.SleepDurationMin / 60 : null,
			unit: 'hr',
			delta: delta(
				data.todaySummary ? data.todaySummary.SleepDurationMin / 60 : null,
				data.yesterdaySummary ? data.yesterdaySummary.SleepDurationMin / 60 : null
			),
			higherIsBetter: true
		},
		{
			label: 'Steps',
			today: data.todaySummary?.Steps ?? null,
			yesterday: data.yesterdaySummary?.Steps ?? null,
			unit: '',
			delta: delta(data.todaySummary?.Steps ?? null, data.yesterdaySummary?.Steps ?? null),
			higherIsBetter: true
		},
		{
			label: 'HRV Deep',
			today: data.todaySummary?.HRVDeepRMSSD ?? null,
			yesterday: data.yesterdaySummary?.HRVDeepRMSSD ?? null,
			unit: 'ms',
			delta: delta(data.todaySummary?.HRVDeepRMSSD ?? null, data.yesterdaySummary?.HRVDeepRMSSD ?? null),
			higherIsBetter: true
		}
	]);
</script>

<svelte:head>
	<title>Dashboard — VitaMetron</title>
</svelte:head>

<div class="flex items-center justify-between mb-6">
	<h1 class="text-2xl font-bold">Dashboard</h1>
	{#if lastUpdated()}
		<span class="text-xs text-gray-400">
			Last updated: {formatDateTime(lastUpdated()!.toISOString())}
		</span>
	{/if}
</div>

<!-- Data quality warning -->
{#if data.dataQuality && !data.dataQuality.IsValidDay}
	<div class="bg-yellow-900/40 border border-yellow-700 rounded-lg px-4 py-3 mb-4 text-sm text-yellow-200">
		<span class="font-semibold">Low data quality</span> — Today's data may be incomplete or unreliable.
		{#if data.dataQuality.MetricsMissing?.length}
			Missing: {data.dataQuality.MetricsMissing.join(', ')}.
		{/if}
	</div>
{/if}

{#if data.dataQuality?.BaselineMaturity === 'cold'}
	<div class="bg-blue-900/40 border border-blue-700 rounded-lg px-4 py-3 mb-4 text-sm text-blue-200">
		<span class="font-semibold">Building baseline</span> — Need {14 - (data.dataQuality.BaselineDays ?? 0)} more valid days for reliable insights.
	</div>
{/if}

<!-- Daily Advice -->
<section class="mb-6">
	<DailyAdviceCard advicePromise={data.todayAdvice} />
</section>

<!-- Header: always visible -->
<div class="grid grid-cols-1 gap-3 lg:grid-cols-2 lg:gap-4 mb-6">
	<VRICard vri={data.todayVRI} />
	<ConditionCard condition={data.latestCondition} />
</div>

<!-- Tabbed sections -->
<DashboardTabs tabs={['現在', '1日', '7日', '30日']}>
	{#snippet panel0()}
		{#if data.dataQuality}
			<div class="flex items-center gap-2 mb-3">
				<span class="text-xs px-2 py-0.5 rounded-full font-medium
					{data.dataQuality.ConfidenceLevel === 'high' ? 'bg-green-800 text-green-200' :
					 data.dataQuality.ConfidenceLevel === 'medium' ? 'bg-yellow-800 text-yellow-200' :
					 'bg-red-800 text-red-200'}">
					Confidence: {data.dataQuality.ConfidenceLevel}
				</span>
				<span class="text-xs text-gray-400">
					({(data.dataQuality.ConfidenceScore * 100).toFixed(0)}%)
				</span>
			</div>
		{/if}
		<div class="grid grid-cols-2 gap-3 lg:grid-cols-3 lg:gap-4">
			<MetricTile label="Resting HR" value={data.todaySummary?.RestingHR ?? '--'} unit="bpm" />
			<MetricTile label="HRV" value={data.todaySummary?.HRVDailyRMSSD ?? '--'} unit="ms" />
			<MetricTile label="SpO2" value={data.todaySummary?.SpO2Avg ?? '--'} unit="%" />
			<MetricTile
				label="Sleep"
				value={data.todaySummary ? (data.todaySummary.SleepDurationMin / 60).toFixed(1) : '--'}
				unit="hr"
			/>
			<MetricTile label="Steps" value={data.todaySummary?.Steps ?? '--'} unit="" />
			<MetricTile label="SRI" value={data.todayVRI?.SRIValue != null ? Math.round(data.todayVRI.SRIValue) : '--'} unit="/100" />
		</div>
		<div class="mt-4">
			<TrendChart conditions={data.recentConditions} />
		</div>
	{/snippet}

	{#snippet panel1()}
		<!-- Time-series section -->
		<p class="text-xs text-gray-400 mb-2">Time Series</p>
		<div class="grid grid-cols-1 gap-3 lg:gap-4">
			<IntradayHRChart todaySamples={data.todayHR} yesterdaySamples={data.yesterdayHR} />
			<SleepStageTimeline todayStages={data.todaySleep} yesterdayStages={data.yesterdaySleep} />
		</div>

		<!-- Snapshot comparison section -->
		<p class="text-xs text-gray-400 mt-4 mb-2">Snapshot Comparison</p>
		<div class="grid grid-cols-2 gap-3 lg:grid-cols-3 lg:gap-4">
			{#each comparisons as comp}
				<ComparisonTile comparison={comp} />
			{/each}
		</div>
	{/snippet}

	{#snippet panel2()}
		<div class="grid grid-cols-1 gap-3 lg:grid-cols-2 lg:gap-4">
			<WeeklyTrendCard
				title="Resting HR"
				summaries={data.weekSummaries}
				extractor={(s) => s.RestingHR}
				color="#ef4444"
				unit="bpm"
			/>
			<WeeklyTrendCard
				title="HRV"
				summaries={data.weekSummaries}
				extractor={(s) => s.HRVDailyRMSSD}
				color="#8b5cf6"
				unit="ms"
			/>
			<WeeklyTrendCard
				title="Sleep"
				summaries={data.weekSummaries}
				extractor={(s) => s.SleepDurationMin / 60}
				color="#06b6d4"
				unit="hr"
			/>
			<WeeklyTrendCard
				title="Steps"
				summaries={data.weekSummaries}
				extractor={(s) => s.Steps}
				color="#22c55e"
			/>
		</div>
		<div class="mt-4">
			<VRITrendChart scores={data.weekVRI} />
		</div>
	{/snippet}

	{#snippet panel3()}
		<div class="grid grid-cols-1 gap-3 lg:grid-cols-2 lg:gap-4">
			<WeeklyTrendCard
				title="Resting HR"
				summaries={data.monthSummaries}
				extractor={(s) => s.RestingHR}
				color="#ef4444"
				unit="bpm"
				rangeLabel="30-day"
			/>
			<WeeklyTrendCard
				title="HRV"
				summaries={data.monthSummaries}
				extractor={(s) => s.HRVDailyRMSSD}
				color="#8b5cf6"
				unit="ms"
				rangeLabel="30-day"
			/>
			<WeeklyTrendCard
				title="Sleep"
				summaries={data.monthSummaries}
				extractor={(s) => s.SleepDurationMin / 60}
				color="#06b6d4"
				unit="hr"
				rangeLabel="30-day"
			/>
			<WeeklyTrendCard
				title="Steps"
				summaries={data.monthSummaries}
				extractor={(s) => s.Steps}
				color="#22c55e"
				rangeLabel="30-day"
			/>
		</div>
		<div class="mt-4">
			<VRITrendChart scores={data.monthVRI} rangeLabel="30-day" />
		</div>
		<div class="mt-4">
			<TrendChart conditions={data.monthConditions} rangeLabel="30-day" />
		</div>
	{/snippet}
</DashboardTabs>
