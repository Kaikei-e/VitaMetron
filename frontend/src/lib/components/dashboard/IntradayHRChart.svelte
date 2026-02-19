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

	const GRID_INTERVAL = 5; // minutes
	const GRID_SIZE = (24 * 60) / GRID_INTERVAL; // 288 points
	const JST_OFFSET_MS = 9 * 60 * 60 * 1000;

	function toMinuteOfDay(iso: string): number {
		const d = new Date(iso);
		const jstMs = d.getTime() + JST_OFFSET_MS;
		const jst = new Date(jstMs);
		return jst.getUTCHours() * 60 + jst.getUTCMinutes();
	}

	function snapToGrid(samples: HeartRateSample[]): (number | null)[] {
		const grid: (number | null)[] = new Array(GRID_SIZE).fill(null);
		for (const s of samples) {
			const min = toMinuteOfDay(s.Time);
			const idx = Math.round(min / GRID_INTERVAL);
			if (idx >= 0 && idx < GRID_SIZE) {
				grid[idx] = s.BPM;
			}
		}
		return grid;
	}

	function lastNonNullIndex(grid: (number | null)[]): number {
		for (let i = grid.length - 1; i >= 0; i--) {
			if (grid[i] !== null) return i;
		}
		return -1;
	}

	let todayGrid = $derived(snapToGrid(todaySamples));
	let yesterdayGrid = $derived(snapToGrid(yesterdaySamples));

	let trimEnd = $derived(Math.max(lastNonNullIndex(todayGrid), lastNonNullIndex(yesterdayGrid)) + 1);

	let labels = $derived(
		Array.from({ length: trimEnd }, (_, i) => {
			const totalMin = i * GRID_INTERVAL;
			const h = Math.floor(totalMin / 60);
			const m = totalMin % 60;
			return h.toString().padStart(2, '0') + ':' + m.toString().padStart(2, '0');
		})
	);

	let datasets = $derived([
		{
			label: 'Today',
			data: todayGrid.slice(0, trimEnd),
			borderColor: '#3b82f6',
			backgroundColor: '#3b82f61a',
			pointRadius: 0,
			borderWidth: 1.5,
			tension: 0.2,
			spanGaps: true
		},
		{
			label: 'Yesterday',
			data: yesterdayGrid.slice(0, trimEnd),
			borderColor: '#9ca3af',
			backgroundColor: 'transparent',
			pointRadius: 0,
			borderWidth: 1,
			borderDash: [4, 2],
			tension: 0.2,
			spanGaps: true
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
