<script lang="ts">
	import BarChart from '$lib/components/charts/BarChart.svelte';
	import type { DivergenceContribution } from '$lib/types/insights';

	let { drivers }: { drivers: DivergenceContribution[] } = $props();

	let sorted = $derived(
		[...drivers].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)).slice(0, 5)
	);

	let labels = $derived(
		sorted.map((d) =>
			d.feature
				.replace(/_/g, ' ')
				.replace(/\b\w/g, (c) => c.toUpperCase())
		)
	);

	let datasets = $derived([
		{
			label: 'Contribution',
			data: sorted.map((d) => d.contribution),
			backgroundColor: sorted.map((d) =>
				d.direction === 'positive' ? 'rgba(34, 197, 94, 0.7)' : 'rgba(239, 68, 68, 0.7)'
			),
			borderColor: sorted.map((d) =>
				d.direction === 'positive' ? '#22c55e' : '#ef4444'
			),
			borderWidth: 1
		}
	]);

	let chartOptions = $derived({
		indexAxis: 'y' as const,
		scales: {
			x: {
				title: { display: true, text: 'Contribution to Gap' }
			}
		},
		plugins: {
			legend: { display: false }
		}
	});
</script>

{#if sorted.length > 0}
	<div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-900 dark:border dark:border-gray-800">
		<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Top Divergence Drivers</h3>
		<BarChart {labels} {datasets} options={chartOptions} height="180px" />
	</div>
{/if}
