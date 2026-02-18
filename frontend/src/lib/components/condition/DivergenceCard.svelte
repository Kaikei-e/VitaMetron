<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import { divergenceStyle } from '$lib/utils/divergence';
	import type { DivergenceDetection, DivergenceModelStatus } from '$lib/types/insights';

	let {
		status,
		latest
	}: {
		status: DivergenceModelStatus | null;
		latest: DivergenceDetection | null;
	} = $props();

	let style = $derived(latest ? divergenceStyle(latest.DivergenceType) : null);

	let progress = $derived.by(() => {
		if (!status) return 0;
		return Math.min(100, Math.round((status.TrainingPairs / status.MinPairsNeeded) * 100));
	});
</script>

<Card>
	<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Body-Mind Gap</h3>

	{#if !status || status.Phase === 'cold_start'}
		<div class="flex flex-col gap-2">
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{status?.Message || 'Record condition logs to enable divergence detection.'}
			</p>
			<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
				<div
					class="bg-blue-500 h-2 rounded-full transition-all"
					style="width: {progress}%"
				></div>
			</div>
			<p class="text-xs text-gray-400">
				{status?.TrainingPairs ?? 0} / {status?.MinPairsNeeded ?? 14} paired observations
			</p>
		</div>
	{:else if latest && latest.DivergenceType !== 'no_condition_log' && latest.DivergenceType !== 'no_biometric_data' && style}
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<span class="inline-block rounded-full px-3 py-1 text-xs font-medium {style.textColor} {style.bgColor}">
					{style.badge}
				</span>
				{#if latest.CuSumAlert}
					<span class="text-xs font-medium text-red-600 dark:text-red-400">Sustained Pattern</span>
				{/if}
			</div>

			<div class="grid grid-cols-3 gap-2 text-center">
				<div>
					<p class="text-lg font-bold text-gray-800 dark:text-gray-100">{Math.round(latest.ActualScore)}</p>
					<p class="text-xs text-gray-500">Actual</p>
				</div>
				<div>
					<p class="text-lg font-bold text-gray-800 dark:text-gray-100">{Math.round(latest.PredictedScore)}</p>
					<p class="text-xs text-gray-500">Expected</p>
				</div>
				<div>
					<p class="text-lg font-bold {style.textColor}">{latest.Residual > 0 ? '+' : ''}{Math.round(latest.Residual)}</p>
					<p class="text-xs text-gray-500">Gap</p>
				</div>
			</div>

			{#if latest.Explanation}
				<p class="text-xs text-gray-500 dark:text-gray-400">{latest.Explanation}</p>
			{/if}

			<div class="flex items-center gap-1">
				<span class="text-xs text-gray-400">Confidence:</span>
				<div class="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
					<div
						class="bg-blue-500 h-1.5 rounded-full"
						style="width: {Math.round(latest.Confidence * 100)}%"
					></div>
				</div>
				<span class="text-xs text-gray-400">{Math.round(latest.Confidence * 100)}%</span>
			</div>
		</div>
	{:else}
		<p class="text-sm text-gray-500 dark:text-gray-400">
			{status.Message || 'Model ready. Divergence data will appear for dates with both condition logs and biometric data.'}
		</p>
	{/if}
</Card>
