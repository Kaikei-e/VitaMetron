<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { ConditionPrediction } from '$lib/types/insights';
	import { humanizeFeature } from '$lib/utils/humanize';

	let { prediction }: { prediction: ConditionPrediction | null } = $props();

	const scoreLabels: Record<number, string> = {
		1: 'Critical',
		2: 'Low',
		3: 'Neutral',
		4: 'Good',
		5: 'Excellent'
	};

	const colorMap: Record<number, string> = {
		1: 'text-condition-1',
		2: 'text-condition-2',
		3: 'text-condition-3',
		4: 'text-condition-4',
		5: 'text-condition-5'
	};

	let rounded = $derived(prediction ? Math.round(prediction.PredictedScore) : null);
	let scoreColor = $derived(rounded ? colorMap[rounded] ?? '' : '');
	let label = $derived(rounded ? scoreLabels[rounded] ?? '' : '');
	let confidencePct = $derived(prediction ? Math.round(prediction.Confidence * 100) : 0);
	let isLowConfidence = $derived(confidencePct < 50);

	let becauseText = $derived.by(() => {
		if (!prediction?.ContributingFactors?.length) return null;
		const top = prediction.ContributingFactors[0];
		const name = humanizeFeature(top.feature);
		const dir = top.direction === 'positive' ? 'higher' : 'lower';
		return `Because your ${name} is ${dir} than usual`;
	});
</script>

<Card>
	<div class="flex items-center gap-1.5">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Tomorrow's Forecast</h3>
		<HelpTooltip text="MLモデルが明日のコンディションを1〜5で予測した値です。過去のバイオメトリクスとコンディション記録のパターンから算出します。Confidenceはモデルの確信度で、70%以上が信頼できる目安です。" />
	</div>
	{#if prediction}
		<div class="mt-3 flex items-baseline gap-3" class:opacity-60={isLowConfidence}>
			<span class="text-5xl font-bold {scoreColor}">{rounded}</span>
			<span class="text-lg font-medium text-gray-600 dark:text-gray-300">{label}</span>
		</div>
		{#if becauseText}
			<p class="mt-2 text-sm text-gray-600 dark:text-gray-400 italic">{becauseText}</p>
		{/if}
		<div class="mt-3 flex items-center gap-2">
			<span class="text-xs text-gray-500 dark:text-gray-400">Confidence</span>
			<div class="flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700">
				<div
					class="h-2 rounded-full transition-all {confidencePct >= 70 ? 'bg-green-500' : confidencePct >= 50 ? 'bg-yellow-500' : 'bg-red-400'}"
					style="width: {confidencePct}%"
				></div>
			</div>
			<span class="text-xs font-medium text-gray-600 dark:text-gray-300">{confidencePct}%</span>
		</div>
		{#if isLowConfidence}
			<p class="mt-1 text-xs text-amber-600 dark:text-amber-400">Low confidence — insufficient data</p>
		{/if}
	{:else}
		<div class="mt-3 flex h-24 items-center justify-center">
			<p class="text-gray-400 dark:text-gray-500">No prediction available</p>
		</div>
	{/if}
</Card>
