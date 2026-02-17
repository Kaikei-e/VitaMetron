<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { ContributingFactor } from '$lib/types/insights';
	import { humanizeFeature } from '$lib/utils/humanize';

	let { factors = [] }: { factors?: ContributingFactor[] } = $props();

	let topFactors = $derived(factors.slice(0, 5));
	let maxAbsImportance = $derived.by(() => {
		if (topFactors.length === 0) return 1;
		return Math.max(...topFactors.map((f) => Math.abs(f.importance)));
	});
</script>

<Card>
	<div class="flex items-center gap-1.5">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Contributing Factors</h3>
		<HelpTooltip text="予測スコアに最も影響した要因のランキングです。バーの長さは影響度を表し、青緑(+)はスコアを押し上げる方向、オレンジ(−)は押し下げる方向を意味します。" />
	</div>
	{#if topFactors.length > 0}
		<div class="mt-3 space-y-2">
			{#each topFactors as factor}
				{@const pct = Math.abs(factor.importance) / maxAbsImportance * 100}
				{@const isPositive = factor.direction === 'positive'}
				<div class="flex items-center gap-2">
					<span class="w-28 shrink-0 truncate text-xs text-gray-600 dark:text-gray-300" title={humanizeFeature(factor.feature)}>
						{humanizeFeature(factor.feature)}
					</span>
					<div class="flex-1 flex items-center h-5">
						<div class="relative w-full h-3 rounded-full bg-gray-100 dark:bg-gray-800">
							<div
								class="absolute top-0 h-3 rounded-full transition-all {isPositive ? 'bg-teal-500' : 'bg-orange-500'}"
								style="width: {pct}%"
							></div>
						</div>
					</div>
					<span class="w-12 shrink-0 text-right text-xs font-medium {isPositive ? 'text-teal-600 dark:text-teal-400' : 'text-orange-600 dark:text-orange-400'}">
						{isPositive ? '+' : ''}{factor.importance.toFixed(2)}
					</span>
				</div>
			{/each}
		</div>
		<div class="mt-2 flex items-center gap-4 text-xs text-gray-400">
			<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-full bg-teal-500"></span> Push up</span>
			<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-full bg-orange-500"></span> Pull down</span>
		</div>
	{:else}
		<p class="mt-3 text-sm text-gray-400 dark:text-gray-500">No factor data available</p>
	{/if}
</Card>
