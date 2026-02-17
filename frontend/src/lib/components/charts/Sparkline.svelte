<script lang="ts">
	import { browser } from '$app/environment';
	import {
		Chart,
		LineController,
		LineElement,
		PointElement,
		LinearScale,
		CategoryScale
	} from 'chart.js';

	Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale);

	let {
		values,
		color = '#3b82f6'
	}: {
		values: number[];
		color?: string;
	} = $props();

	let canvas: HTMLCanvasElement;
	let chart: Chart<'line'> | null = null;

	$effect(() => {
		if (!browser || !canvas) return;

		chart?.destroy();
		chart = new Chart(canvas, {
			type: 'line',
			data: {
				labels: values.map((_, i) => String(i)),
				datasets: [
					{
						data: values,
						borderColor: color,
						borderWidth: 1.5,
						pointRadius: 0,
						tension: 0.3,
						fill: false
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: { tooltip: { enabled: false }, legend: { display: false } },
				scales: {
					x: { display: false },
					y: { display: false }
				}
			}
		});

		return () => {
			chart?.destroy();
			chart = null;
		};
	});
</script>

<div class="inline-block h-8 w-24">
	<canvas bind:this={canvas}></canvas>
</div>
