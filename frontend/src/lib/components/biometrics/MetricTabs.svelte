<script lang="ts">
	import MetricDetail from './MetricDetail.svelte';
	import BarChart from '$lib/components/charts/BarChart.svelte';
	import type { DailySummary } from '$lib/types/biometrics';

	let { summary }: { summary: DailySummary | null } = $props();

	let activeTab = $state<'heart' | 'sleep' | 'activity'>('heart');
	const tabs = ['heart', 'sleep', 'activity'] as const;

	let heartMetrics = $derived(
		summary
			? [
					{ label: 'Resting HR', value: summary.RestingHR, unit: 'bpm' },
					{ label: 'Average HR', value: summary.AvgHR, unit: 'bpm' },
					{ label: 'Max HR', value: summary.MaxHR, unit: 'bpm' },
					{ label: 'HRV Daily', value: summary.HRVDailyRMSSD?.toFixed(1) ?? '--', unit: 'ms' },
					{ label: 'HRV Deep', value: summary.HRVDeepRMSSD?.toFixed(1) ?? '--', unit: 'ms' },
					{ label: 'SpO2 Avg', value: summary.SpO2Avg?.toFixed(1) ?? '--', unit: '%' },
					{ label: 'SpO2 Min', value: summary.SpO2Min?.toFixed(1) ?? '--', unit: '%' },
					{ label: 'SpO2 Max', value: summary.SpO2Max?.toFixed(1) ?? '--', unit: '%' }
				]
			: []
	);

	let sleepMetrics = $derived(
		summary
			? [
					{
						label: 'Duration',
						value: `${Math.floor(summary.SleepDurationMin / 60)}h ${summary.SleepDurationMin % 60}m`
					},
					{ label: 'Onset Latency', value: summary.SleepOnsetLatency, unit: 'min' },
					{ label: 'Minutes Asleep', value: summary.SleepMinutesAsleep, unit: 'min' },
					{ label: 'Minutes Awake', value: summary.SleepMinutesAwake, unit: 'min' }
				]
			: []
	);

	let sleepStageLabels = $derived(['Deep', 'Light', 'REM', 'Wake']);
	let sleepStageDatasets = $derived(
		summary
			? [
					{
						label: 'Minutes',
						data: [
							summary.SleepDeepMin,
							summary.SleepLightMin,
							summary.SleepREMMin,
							summary.SleepWakeMin
						],
						backgroundColor: ['#6366f1', '#60a5fa', '#34d399', '#fbbf24']
					}
				]
			: []
	);

	let activityMetrics = $derived(
		summary
			? [
					{ label: 'Steps', value: summary.Steps.toLocaleString() },
					{ label: 'Distance', value: summary.DistanceKM.toFixed(2), unit: 'km' },
					{ label: 'Calories', value: summary.CaloriesTotal.toLocaleString(), unit: 'kcal' },
					{ label: 'Active Calories', value: summary.CaloriesActive.toLocaleString(), unit: 'kcal' },
					{ label: 'Active Zone Min', value: summary.ActiveZoneMin, unit: 'min' },
					{ label: 'Floors', value: summary.Floors }
				]
			: []
	);

	function handleTabKeydown(e: KeyboardEvent) {
		const idx = tabs.indexOf(activeTab);
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			activeTab = tabs[(idx + 1) % tabs.length];
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			activeTab = tabs[(idx - 1 + tabs.length) % tabs.length];
		}
	}
</script>

<div class="mt-4">
	<div class="flex gap-2 border-b border-gray-200 mb-4 dark:border-gray-700" role="tablist" aria-label="Biometric categories">
		{#each tabs as tab}
			<button
				role="tab"
				aria-selected={activeTab === tab}
				id="tab-{tab}"
				aria-controls="panel-{tab}"
				tabindex={activeTab === tab ? 0 : -1}
				class="min-h-12 px-3 py-2 text-sm font-medium transition-colors"
				class:border-b-2={activeTab === tab}
				class:border-blue-600={activeTab === tab}
				class:text-blue-600={activeTab === tab}
				class:text-gray-500={activeTab !== tab}
				onclick={() => (activeTab = tab)}
				onkeydown={handleTabKeydown}
			>
				{tab[0].toUpperCase() + tab.slice(1)}
			</button>
		{/each}
	</div>

	{#if !summary}
		<p class="p-4 text-gray-400">No data available for this date.</p>
	{:else if activeTab === 'heart'}
		<div role="tabpanel" id="panel-heart" aria-labelledby="tab-heart">
			<MetricDetail metrics={heartMetrics} />
		</div>
	{:else if activeTab === 'sleep'}
		<div role="tabpanel" id="panel-sleep" aria-labelledby="tab-sleep">
			<MetricDetail metrics={sleepMetrics} />
			{#if sleepStageDatasets.length > 0}
				<div class="mt-4">
					<h4 class="text-sm font-medium text-gray-500 mb-2">Sleep Stages</h4>
					<BarChart labels={sleepStageLabels} datasets={sleepStageDatasets} height="200px" />
				</div>
			{/if}
		</div>
	{:else if activeTab === 'activity'}
		<div role="tabpanel" id="panel-activity" aria-labelledby="tab-activity">
			<MetricDetail metrics={activityMetrics} />
		</div>
	{/if}
</div>
