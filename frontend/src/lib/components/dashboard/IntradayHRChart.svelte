<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import type { HeartRateSample } from '$lib/types/biometrics';

	let {
		todaySamples,
		yesterdaySamples
	}: {
		todaySamples: HeartRateSample[];
		yesterdaySamples: HeartRateSample[];
	} = $props();

	function toTimeLabel(iso: string): string {
		const d = new Date(iso);
		return d.getUTCHours().toString().padStart(2, '0') + ':' + d.getUTCMinutes().toString().padStart(2, '0');
	}

	let labels = $derived(
		yesterdaySamples.length >= todaySamples.length
			? yesterdaySamples.map((s) => toTimeLabel(s.Time))
			: todaySamples.map((s) => toTimeLabel(s.Time))
	);

	let datasets = $derived([
		{
			label: 'Today',
			data: todaySamples.map((s) => s.BPM),
			borderColor: '#3b82f6',
			backgroundColor: '#3b82f61a',
			pointRadius: 0,
			borderWidth: 1.5,
			tension: 0.2
		},
		{
			label: 'Yesterday',
			data: yesterdaySamples.map((s) => s.BPM),
			borderColor: '#9ca3af',
			backgroundColor: 'transparent',
			pointRadius: 0,
			borderWidth: 1,
			borderDash: [4, 2],
			tension: 0.2
		}
	]);

	let hasData = $derived(todaySamples.length > 0 || yesterdaySamples.length > 0);
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Heart Rate Intraday</h3>
	{#if hasData}
		<div class="h-[160px] lg:h-[200px]" role="img" aria-label="Heart rate intraday chart">
			<LineChart
				{labels}
				{datasets}
				height="100%"
				options={{
					plugins: {
						tooltip: { mode: 'index', intersect: false },
						decimation: { enabled: true, algorithm: 'min-max' }
					},
					scales: {
						x: {
							ticks: {
								maxTicksLimit: 12,
								autoSkip: true
							}
						}
					}
				}}
			/>
		</div>
	{:else}
		<div class="flex items-center justify-center text-gray-400 h-[160px] lg:h-[200px]">
			No heart rate data
		</div>
	{/if}
</Card>
