<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import type { ConditionLog } from '$lib/types/condition';

	let { conditions = [] }: { conditions?: ConditionLog[] } = $props();

	let labels = $derived(
		conditions.map((c) =>
			new Date(c.LoggedAt).toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' })
		)
	);

	let datasets = $derived([
		{
			label: 'Overall',
			data: conditions.map((c) => c.Overall),
			borderColor: '#3b82f6',
			backgroundColor: 'rgba(59, 130, 246, 0.1)',
			fill: true,
			tension: 0.3
		}
	]);

	let ariaLabel = $derived(
		conditions.length > 0
			? `7-day condition trend: scores ${conditions.map((c) => c.Overall).join(', ')}`
			: '7-day condition trend: no data'
	);
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 mb-4">7-Day Trend</h3>
	{#if conditions.length > 0}
		<div role="img" aria-label={ariaLabel}>
			<LineChart
				{labels}
				{datasets}
				options={{ scales: { y: { min: 1, max: 5, ticks: { stepSize: 1 } } } }}
				height="192px"
			/>
		</div>
	{:else}
		<div class="flex h-48 items-center justify-center text-gray-400">
			No trend data available
		</div>
	{/if}
</Card>
