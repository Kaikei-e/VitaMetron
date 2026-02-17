<script lang="ts">
	import LineChart from '$lib/components/charts/LineChart.svelte';
	import type { DivergenceDetection } from '$lib/types/insights';

	let { detections }: { detections: DivergenceDetection[] } = $props();

	let filtered = $derived(
		detections.filter(
			(d) => d.DivergenceType !== 'no_condition_log' && d.DivergenceType !== 'no_biometric_data'
		)
	);

	let labels = $derived(filtered.map((d) => d.Date.slice(5)));

	let datasets = $derived([
		{
			label: 'Actual',
			data: filtered.map((d) => d.ActualScore),
			borderColor: '#3b82f6',
			backgroundColor: 'rgba(59, 130, 246, 0.1)',
			borderWidth: 2,
			pointRadius: 3,
			tension: 0.3
		},
		{
			label: 'Expected',
			data: filtered.map((d) => d.PredictedScore),
			borderColor: '#9ca3af',
			borderDash: [5, 5],
			borderWidth: 2,
			pointRadius: 2,
			tension: 0.3
		}
	]);

	let chartOptions = $derived({
		scales: {
			y: {
				min: 0,
				max: 5,
				title: { display: true, text: 'Score' }
			}
		},
		plugins: {
			tooltip: {
				callbacks: {
					afterBody(items: any[]) {
						const idx = items[0]?.dataIndex;
						if (idx != null && filtered[idx]) {
							const d = filtered[idx];
							return `Residual: ${d.Residual > 0 ? '+' : ''}${d.Residual.toFixed(2)}\nType: ${d.DivergenceType.replace(/_/g, ' ')}`;
						}
						return '';
					}
				}
			}
		}
	});
</script>

{#if filtered.length > 0}
	<div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-900 dark:border dark:border-gray-800">
		<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Actual vs Expected Condition</h3>
		<LineChart {labels} {datasets} options={chartOptions} height="220px" />
	</div>
{/if}
