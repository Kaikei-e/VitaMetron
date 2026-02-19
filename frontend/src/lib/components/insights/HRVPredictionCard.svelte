<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { HRVPrediction } from '$lib/types/insights';
	import { humanizeFeature } from '$lib/utils/humanize';

	let { prediction }: { prediction: HRVPrediction | null } = $props();

	let directionArrow = $derived.by(() => {
		if (!prediction) return '';
		switch (prediction.PredictedDirection) {
			case 'above':
				return '\u2191';
			case 'below':
				return '\u2193';
			default:
				return '\u2192';
		}
	});

	let directionLabel = $derived.by(() => {
		if (!prediction) return '';
		switch (prediction.PredictedDirection) {
			case 'above':
				return 'Above baseline';
			case 'below':
				return 'Below baseline';
			default:
				return 'Near baseline';
		}
	});

	let directionColor = $derived.by(() => {
		if (!prediction) return '';
		switch (prediction.PredictedDirection) {
			case 'above':
				return 'text-green-600 dark:text-green-400';
			case 'below':
				return 'text-red-500 dark:text-red-400';
			default:
				return 'text-gray-500 dark:text-gray-400';
		}
	});

	let confidencePct = $derived(prediction ? Math.round(prediction.Confidence * 100) : 0);

	let topDrivers = $derived.by(() => {
		if (!prediction?.TopDrivers) return [];
		return prediction.TopDrivers.slice(0, 3);
	});
</script>

<Card>
	<div class="flex items-center gap-1.5">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">HRV Prediction</h3>
		<HelpTooltip text="HRV（心拍変動）の翌日予測です。Z-scoreは過去のベースラインとの差を標準偏差で表し、+なら平均より高く−なら低いことを示します。Above/Belowはベースラインとの比較方向です。" />
	</div>
	{#if prediction}
		<div class="mt-2 flex items-baseline gap-2">
			<span class="text-3xl font-bold {directionColor}">{directionArrow}</span>
			<span class="text-sm font-medium {directionColor}">{directionLabel}</span>
		</div>
		<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
			Z-score: {prediction.PredictedZScore >= 0 ? '+' : ''}{prediction.PredictedZScore.toFixed(2)}
		</p>
		<div class="mt-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {confidencePct >= 70 ? 'bg-green-100 text-green-800 dark:bg-green-800/20 dark:text-green-200' : confidencePct >= 50 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800/20 dark:text-yellow-200' : 'bg-red-100 text-red-800 dark:bg-red-800/20 dark:text-red-200'}">
			Confidence: {confidencePct}%
		</div>
		{#if topDrivers.length > 0}
			<div class="mt-3 space-y-1">
				<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Top Drivers</p>
				{#each topDrivers as driver}
					<div class="flex items-center gap-2 text-xs">
						<span class="w-3 {driver.direction === 'positive' ? 'text-teal-500' : 'text-orange-500'}">
							{driver.direction === 'positive' ? '\u25B2' : '\u25BC'}
						</span>
						<span class="text-gray-600 dark:text-gray-300">{humanizeFeature(driver.feature)}</span>
					</div>
				{/each}
			</div>
		{/if}
	{:else}
		<div class="mt-2 flex h-20 items-center justify-center">
			<p class="text-sm text-gray-400 dark:text-gray-500">No HRV prediction</p>
		</div>
	{/if}
</Card>
