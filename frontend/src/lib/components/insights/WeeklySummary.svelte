<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { WeeklyInsight } from '$lib/types/insights';

	let { insight }: { insight: WeeklyInsight | null } = $props();

	const trendArrows: Record<string, string> = {
		improving: '\u2197',
		declining: '\u2198',
		stable: '\u2192'
	};

	const trendColors: Record<string, string> = {
		improving: 'text-green-600 dark:text-green-400',
		declining: 'text-red-500 dark:text-red-400',
		stable: 'text-gray-500 dark:text-gray-400'
	};

	let trendArrow = $derived(insight ? trendArrows[insight.Trend] ?? '\u2192' : '');
	let trendColor = $derived(insight ? trendColors[insight.Trend] ?? '' : '');
	let trendLabel = $derived(insight ? insight.Trend.charAt(0).toUpperCase() + insight.Trend.slice(1) : '');

	function formatWeekRange(start: string, end: string): string {
		const s = new Date(start);
		const e = new Date(end);
		const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });
		return `${fmt(s)} - ${fmt(e)}`;
	}
</script>

<Card>
	<div class="flex items-center gap-1.5">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Week in Review</h3>
		<HelpTooltip text="過去1週間のコンディション平均スコアとトレンドです。Improvingは改善傾向、Decliningは低下傾向、Stableは安定を意味します。" />
	</div>
	{#if insight}
		<p class="mt-1 text-xs text-gray-400">
			{formatWeekRange(insight.WeekStart, insight.WeekEnd)}
		</p>
		<div class="mt-3 flex items-baseline gap-4">
			<div>
				<span class="text-xs text-gray-500 dark:text-gray-400">Avg Score</span>
				<p class="text-2xl font-bold">
					{insight.AvgScore != null ? insight.AvgScore.toFixed(1) : '--'}
				</p>
			</div>
			<div>
				<span class="text-xs text-gray-500 dark:text-gray-400">Trend</span>
				<p class="text-lg font-semibold {trendColor}">
					{trendArrow} {trendLabel}
				</p>
			</div>
		</div>
		{#if insight.TopFactors.length > 0}
			<div class="mt-3 flex flex-wrap gap-1.5">
				{#each insight.TopFactors as factor}
					<span class="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
						{factor}
					</span>
				{/each}
			</div>
		{/if}
		{#if insight.RiskSummary.length > 0}
			<div class="mt-2 flex flex-wrap gap-1.5">
				{#each insight.RiskSummary as risk}
					<span class="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
						{'\u26A0'} {risk}
					</span>
				{/each}
			</div>
		{/if}
	{:else}
		<div class="mt-3 flex h-24 items-center justify-center">
			<p class="text-gray-400 dark:text-gray-500">No weekly data available</p>
		</div>
	{/if}
</Card>
