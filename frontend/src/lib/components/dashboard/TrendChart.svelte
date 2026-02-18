<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import { formatShortDate } from '$lib/utils/date';
	import type { ConditionLog } from '$lib/types/condition';

	let { conditions = [], rangeLabel = '7-day' }: { conditions?: ConditionLog[]; rangeLabel?: string } = $props();

	let labels = $derived(conditions.map((c) => formatShortDate(c.LoggedAt)));

	let datasets = $derived([
		{
			label: 'Well-being',
			data: conditions.map((c) => c.OverallVAS),
			borderColor: '#3b82f6',
			backgroundColor: 'rgba(59, 130, 246, 0.1)',
			fill: true,
			tension: 0.3
		}
	]);

	let ariaLabel = $derived(
		conditions.length > 0
			? `${rangeLabel} condition trend: scores ${conditions.map((c) => c.OverallVAS).join(', ')}`
			: `${rangeLabel} condition trend: no data`
	);
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 mb-4">{rangeLabel} Trend</h3>
	{#if conditions.length > 0}
		<div role="img" aria-label={ariaLabel}>
			<LineChart
				{labels}
				{datasets}
				options={{ scales: { y: { min: 0, max: 100, ticks: { stepSize: 25 } } } }}
				height="192px"
			/>
		</div>
	{:else}
		<div class="flex h-48 items-center justify-center text-gray-400">
			No trend data available
		</div>
	{/if}
</Card>
