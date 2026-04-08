<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { CircadianScore } from '$lib/types/biometrics';

	let { scores }: { scores: CircadianScore[] } = $props();

	const W = 320;
	const H = 180;
	const PAD = { top: 20, right: 20, bottom: 30, left: 45 };
	const PLOT_W = W - PAD.left - PAD.right;
	const PLOT_H = H - PAD.top - PAD.bottom;

	// Filter scores with sleep midpoint data
	let validScores = $derived(
		scores.filter((s) => s.SleepMidpointHour != null).slice(-7)
	);

	// Y axis: time of day in hours (inverted: earlier at top)
	// Typically sleep midpoint falls between 1:00-6:00
	let yRange = $derived(() => {
		if (!validScores.length) return { min: 1, max: 6 };
		const midpoints = validScores.map((s) => s.SleepMidpointHour!);
		const minH = Math.floor(Math.min(...midpoints) - 1);
		const maxH = Math.ceil(Math.max(...midpoints) + 1);
		return { min: Math.max(0, minH), max: Math.min(24, maxH) };
	});

	function yPos(hour: number): number {
		const range = yRange();
		return PAD.top + ((hour - range.min) / (range.max - range.min)) * PLOT_H;
	}

	function xPos(index: number): number {
		if (validScores.length <= 1) return PAD.left + PLOT_W / 2;
		return PAD.left + (index / (validScores.length - 1)) * PLOT_W;
	}

	function formatHour(h: number): string {
		const hours = Math.floor(h);
		const mins = Math.round((h - hours) * 60);
		return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
	}

	function formatDate(dateStr: string): string {
		const d = new Date(dateStr);
		return `${d.getMonth() + 1}/${d.getDate()}`;
	}

	// Mean midpoint line
	let meanMidpoint = $derived(() => {
		if (!validScores.length) return null;
		const sum = validScores.reduce((a, s) => a + (s.SleepMidpointHour ?? 0), 0);
		return sum / validScores.length;
	});

	// Social jetlag from latest score
	let latestJetlag = $derived(
		validScores.length > 0
			? validScores[validScores.length - 1].SocialJetlagMin
			: null
	);
</script>

<Card>
	<div class="flex items-center gap-1.5 mb-2">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Sleep Midpoint</h3>
		<HelpTooltip
			text="過去7日間の睡眠中間点（入眠〜起床の中間時刻）の推移。水平線は平均値。ばらつきが小さいほど概日リズムが安定しています。Social jetlag = 平日と休日の睡眠中間点の差。"
		/>
	</div>

	{#if validScores.length >= 2}
		<svg viewBox="0 0 {W} {H}" class="w-full">
			<!-- Y axis grid lines + labels -->
			{#each Array(yRange().max - yRange().min + 1) as _, i}
				{@const hour = yRange().min + i}
				{@const y = yPos(hour)}
				<line
					x1={PAD.left}
					y1={y}
					x2={PAD.left + PLOT_W}
					y2={y}
					class="stroke-gray-200 dark:stroke-gray-700"
					stroke-width="0.5"
				/>
				<text x={PAD.left - 5} y={y} text-anchor="end" dominant-baseline="central" class="fill-gray-400 text-[9px]">
					{formatHour(hour)}
				</text>
			{/each}

			<!-- Mean midpoint line -->
			{#if meanMidpoint() != null}
				{@const my = yPos(meanMidpoint()!)}
				<line
					x1={PAD.left}
					y1={my}
					x2={PAD.left + PLOT_W}
					y2={my}
					stroke="#22c55e"
					stroke-width="1"
					stroke-dasharray="4,3"
					opacity="0.6"
				/>
				<text x={PAD.left + PLOT_W + 2} y={my} class="fill-green-500 text-[8px]" dominant-baseline="central">
					avg
				</text>
			{/if}

			<!-- Data points and line -->
			{#each validScores as score, i}
				{@const x = xPos(i)}
				{@const midpoint = score.SleepMidpointHour!}
				{@const y = yPos(midpoint)}

				<!-- Connect to next point -->
				{#if i < validScores.length - 1}
					{@const nextScore = validScores[i + 1]}
					{#if nextScore.SleepMidpointHour != null}
						{@const nx = xPos(i + 1)}
						{@const ny = yPos(nextScore.SleepMidpointHour)}
						<line x1={x} y1={y} x2={nx} y2={ny} stroke="#6366f1" stroke-width="1.5" opacity="0.5" />
					{/if}
				{/if}

				<!-- Midpoint dot -->
				<circle cx={x} cy={y} r="4" fill="#6366f1" />

				<!-- Date label -->
				<text x={x} y={H - 5} text-anchor="middle" class="fill-gray-400 text-[8px]">
					{formatDate(score.Date)}
				</text>
			{/each}
		</svg>

		<!-- Summary stats -->
		<div class="flex justify-center gap-4 mt-1 text-xs text-gray-400">
			{#if validScores[validScores.length - 1]?.SleepMidpointVarMin != null}
				<span>
					SD: {validScores[validScores.length - 1].SleepMidpointVarMin?.toFixed(0)}min
				</span>
			{/if}
			{#if latestJetlag != null}
				<span>
					Social jetlag: {latestJetlag.toFixed(0)}min
				</span>
			{/if}
		</div>
	{:else}
		<p class="text-center text-sm text-gray-400 py-8">Need 2+ days of sleep data</p>
	{/if}
</Card>
