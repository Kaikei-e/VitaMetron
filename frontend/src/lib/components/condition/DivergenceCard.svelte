<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import type { DivergenceDetection, DivergenceModelStatus } from '$lib/types/insights';

	let {
		status,
		latest
	}: {
		status: DivergenceModelStatus | null;
		latest: DivergenceDetection | null;
	} = $props();

	let typeColor = $derived.by(() => {
		if (!latest) return 'text-gray-500';
		switch (latest.DivergenceType) {
			case 'feeling_better_than_expected':
				return 'text-amber-600 dark:text-amber-400';
			case 'feeling_worse_than_expected':
				return 'text-blue-600 dark:text-blue-400';
			case 'aligned':
				return 'text-green-600 dark:text-green-400';
			default:
				return 'text-gray-500';
		}
	});

	let typeBadge = $derived.by(() => {
		if (!latest) return '';
		switch (latest.DivergenceType) {
			case 'feeling_better_than_expected':
				return 'Feeling Better Than Expected';
			case 'feeling_worse_than_expected':
				return 'Feeling Worse Than Expected';
			case 'aligned':
				return 'Aligned';
			case 'no_condition_log':
				return 'No Condition Log';
			case 'no_biometric_data':
				return 'No Biometric Data';
			default:
				return latest.DivergenceType;
		}
	});

	let typeBgColor = $derived.by(() => {
		if (!latest) return 'bg-gray-100 dark:bg-gray-800';
		switch (latest.DivergenceType) {
			case 'feeling_better_than_expected':
				return 'bg-amber-50 dark:bg-amber-900/20';
			case 'feeling_worse_than_expected':
				return 'bg-blue-50 dark:bg-blue-900/20';
			case 'aligned':
				return 'bg-green-50 dark:bg-green-900/20';
			default:
				return 'bg-gray-100 dark:bg-gray-800';
		}
	});

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
	{:else if latest && latest.DivergenceType !== 'no_condition_log' && latest.DivergenceType !== 'no_biometric_data'}
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<span class="inline-block rounded-full px-3 py-1 text-xs font-medium {typeColor} {typeBgColor}">
					{typeBadge}
				</span>
				{#if latest.CuSumAlert}
					<span class="text-xs font-medium text-red-600 dark:text-red-400">Sustained Pattern</span>
				{/if}
			</div>

			<div class="grid grid-cols-3 gap-2 text-center">
				<div>
					<p class="text-lg font-bold text-gray-800 dark:text-gray-100">{latest.ActualScore.toFixed(1)}</p>
					<p class="text-xs text-gray-500">Actual</p>
				</div>
				<div>
					<p class="text-lg font-bold text-gray-800 dark:text-gray-100">{latest.PredictedScore.toFixed(1)}</p>
					<p class="text-xs text-gray-500">Expected</p>
				</div>
				<div>
					<p class="text-lg font-bold {typeColor}">{latest.Residual > 0 ? '+' : ''}{latest.Residual.toFixed(2)}</p>
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
