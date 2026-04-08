<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import type { CircadianScore } from '$lib/types/biometrics';

	let {
		scores,
		height = '160px',
		rangeLabel = '7-day'
	}: {
		scores: CircadianScore[];
		height?: string;
		rangeLabel?: string;
	} = $props();

	let labels = $derived(
		scores.map((s) =>
			new Date(s.Date).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' })
		)
	);

	let values = $derived(scores.map((s) => s.CHSScore));

	let datasets = $derived([
		{
			label: 'CHS',
			data: values,
			borderColor: '#06b6d4',
			backgroundColor: '#06b6d41a',
			fill: true,
			tension: 0.3
		}
	]);

	let ariaLabel = $derived(
		values.length > 0
			? `CHS ${rangeLabel} trend: ${values.map((v) => Math.round(v)).join(', ')}`
			: `CHS ${rangeLabel} trend: no data`
	);
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Circadian Health Trend</h3>
	{#if scores.length > 0}
		<div role="img" aria-label={ariaLabel}>
			<LineChart {labels} {datasets} {height} />
		</div>
	{:else}
		<div class="flex items-center justify-center text-gray-400" style:height>
			No circadian trend data available
		</div>
	{/if}
</Card>
