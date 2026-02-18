<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import type { DailySummary } from '$lib/types/biometrics';

	let {
		title,
		summaries,
		extractor,
		color = '#3b82f6',
		unit = '',
		height = '160px',
		rangeLabel = '7-day'
	}: {
		title: string;
		summaries: DailySummary[];
		extractor: (s: DailySummary) => number;
		color?: string;
		unit?: string;
		height?: string;
		rangeLabel?: string;
	} = $props();

	let labels = $derived(
		summaries.map((s) =>
			new Date(s.Date).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' })
		)
	);

	let values = $derived(summaries.map(extractor));

	let datasets = $derived([
		{
			label: title,
			data: values,
			borderColor: color,
			backgroundColor: color + '1a',
			fill: true,
			tension: 0.3
		}
	]);

	let ariaLabel = $derived(
		values.length > 0
			? `${title} ${rangeLabel} trend: ${values.join(', ')}${unit ? ' ' + unit : ''}`
			: `${title} ${rangeLabel} trend: no data`
	);
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">{title}</h3>
	{#if summaries.length > 0}
		<div role="img" aria-label={ariaLabel}>
			<LineChart {labels} {datasets} {height} />
		</div>
	{:else}
		<div class="flex items-center justify-center text-gray-400" style:height>
			No trend data available
		</div>
	{/if}
</Card>
