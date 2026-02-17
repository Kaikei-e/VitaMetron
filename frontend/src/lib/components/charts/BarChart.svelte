<script lang="ts">
	import { browser } from '$app/environment';
	import {
		Chart,
		BarController,
		BarElement,
		LinearScale,
		CategoryScale,
		Tooltip,
		Legend
	} from 'chart.js';
	import type { ChartData, ChartOptions } from 'chart.js';

	Chart.register(BarController, BarElement, LinearScale, CategoryScale, Tooltip, Legend);

	let {
		labels,
		datasets,
		options = {},
		height = '200px'
	}: {
		labels: string[];
		datasets: ChartData<'bar'>['datasets'];
		options?: ChartOptions<'bar'>;
		height?: string;
	} = $props();

	let canvas: HTMLCanvasElement;
	let chart: Chart<'bar'> | null = null;

	function isDark(): boolean {
		return browser && window.matchMedia('(prefers-color-scheme: dark)').matches;
	}

	$effect(() => {
		if (!browser || !canvas) return;

		const dark = isDark();
		const textColor = dark ? '#9ca3af' : '#6b7280';
		const gridColor = dark ? '#374151' : '#e5e7eb';

		chart?.destroy();
		chart = new Chart(canvas, {
			type: 'bar',
			data: { labels, datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					tooltip: { enabled: true },
					legend: { labels: { color: textColor } }
				},
				scales: {
					x: { grid: { display: false }, ticks: { color: textColor } },
					y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } }
				},
				...options
			}
		});

		return () => {
			chart?.destroy();
			chart = null;
		};
	});
</script>

<div style:height>
	<canvas bind:this={canvas}></canvas>
</div>
