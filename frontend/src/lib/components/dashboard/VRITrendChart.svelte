<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import type { VRIScore } from '$lib/types/biometrics';

	let {
		scores,
		height = '160px'
	}: {
		scores: VRIScore[];
		height?: string;
	} = $props();

	let labels = $derived(
		scores.map((s) =>
			new Date(s.Date).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' })
		)
	);

	let values = $derived(scores.map((s) => s.VRIScore));

	let datasets = $derived([
		{
			label: 'VRI',
			data: values,
			borderColor: '#8b5cf6',
			backgroundColor: '#8b5cf61a',
			fill: true,
			tension: 0.3
		}
	]);

	let ariaLabel = $derived(
		values.length > 0
			? `VRI 7-day trend: ${values.map((v) => Math.round(v)).join(', ')}`
			: 'VRI 7-day trend: no data'
	);
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">VRI Trend</h3>
	{#if scores.length > 0}
		<div role="img" aria-label={ariaLabel}>
			<LineChart {labels} {datasets} {height} />
		</div>
	{:else}
		<div class="flex items-center justify-center text-gray-400" style:height>
			No VRI trend data available
		</div>
	{/if}
</Card>
