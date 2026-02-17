<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import BarChart from '$lib/components/charts/BarChart.svelte';
	import type { SleepStageEntry } from '$lib/types/biometrics';

	let {
		todayStages,
		yesterdayStages
	}: {
		todayStages: SleepStageEntry[];
		yesterdayStages: SleepStageEntry[];
	} = $props();

	const stageConfig = [
		{ key: 'deep', label: 'Deep', color: '#6366f1' },
		{ key: 'light', label: 'Light', color: '#60a5fa' },
		{ key: 'rem', label: 'REM', color: '#34d399' },
		{ key: 'wake', label: 'Wake', color: '#fbbf24' }
	] as const;

	function stageMinutes(stages: SleepStageEntry[]): Record<string, number> {
		const totals: Record<string, number> = { deep: 0, light: 0, rem: 0, wake: 0 };
		for (const s of stages) {
			if (s.Stage in totals) {
				totals[s.Stage] += s.Seconds / 60;
			}
		}
		return totals;
	}

	let todayMin = $derived(stageMinutes(todayStages));
	let yesterdayMin = $derived(stageMinutes(yesterdayStages));

	let datasets = $derived(
		stageConfig.map((sc) => ({
			label: sc.label,
			data: [Math.round(todayMin[sc.key]), Math.round(yesterdayMin[sc.key])],
			backgroundColor: sc.color
		}))
	);

	let hasData = $derived(todayStages.length > 0 || yesterdayStages.length > 0);
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Sleep Stages</h3>
	{#if hasData}
		<div class="h-[120px]" role="img" aria-label="Sleep stages timeline">
			<BarChart
				labels={['Today', 'Yesterday']}
				{datasets}
				height="100%"
				options={{
					indexAxis: 'y',
					scales: {
						x: {
							stacked: true,
							title: { display: true, text: 'min' }
						},
						y: { stacked: true }
					},
					plugins: {
						legend: { position: 'bottom', labels: { boxWidth: 12, padding: 8 } }
					}
				}}
			/>
		</div>
	{:else}
		<div class="flex items-center justify-center text-gray-400 h-[120px]">No sleep data</div>
	{/if}
</Card>
