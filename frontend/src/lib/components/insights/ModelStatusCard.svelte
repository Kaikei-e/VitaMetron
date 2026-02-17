<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { HRVModelStatus } from '$lib/types/insights';
	import { humanizeFeature } from '$lib/utils/humanize';

	let { status }: { status: HRVModelStatus | null } = $props();

	let showMetrics = $state(false);

	let metricsEntries = $derived.by(() => {
		if (!status?.CVMetrics) return [];
		return Object.entries(status.CVMetrics);
	});
</script>

<Card>
	<div class="flex items-center gap-1.5">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Model Status</h3>
		<HelpTooltip text="HRV予測モデルの状態です。Readyは予測可能、トレーニング日数が多いほど精度が高くなります。CV Metricsはモデルの精度指標（交差検証結果）です。" />
	</div>
	{#if status}
		<div class="mt-2 flex items-center gap-2">
			<span
				class="inline-block h-2.5 w-2.5 rounded-full {status.IsReady ? 'bg-green-500' : 'bg-red-500'}"
				aria-hidden="true"
			></span>
			<span class="text-sm font-medium {status.IsReady ? 'text-green-700 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
				{status.IsReady ? 'Ready' : 'Not Ready'}
			</span>
			{#if status.ModelVersion}
				<span class="text-xs text-gray-400">{status.ModelVersion}</span>
			{/if}
			{#if status.TrainingDays > 0}
				<span class="text-xs text-gray-400">({status.TrainingDays} days)</span>
			{/if}
		</div>
		{#if metricsEntries.length > 0}
			<button
				class="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
				onclick={() => (showMetrics = !showMetrics)}
			>
				{showMetrics ? '\u25BC Hide metrics' : '\u25B6 Show full metrics'}
			</button>
			{#if showMetrics}
				<div class="mt-2 space-y-1">
					{#each metricsEntries as [key, value]}
						<div class="flex justify-between text-xs">
							<span class="text-gray-500 dark:text-gray-400">{humanizeFeature(key)}</span>
							<span class="font-mono text-gray-700 dark:text-gray-200">{typeof value === 'number' ? value.toFixed(4) : value}</span>
						</div>
					{/each}
				</div>
			{/if}
		{/if}
		{#if status.StableFeatures?.length}
			<div class="mt-2">
				<p class="text-xs text-gray-500 dark:text-gray-400">Stable Features</p>
				<div class="mt-1 flex flex-wrap gap-1">
					{#each status.StableFeatures as feature}
						<span class="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">
							{humanizeFeature(feature)}
						</span>
					{/each}
				</div>
			</div>
		{/if}
	{:else}
		<div class="mt-2 flex h-16 items-center justify-center">
			<p class="text-sm text-gray-400 dark:text-gray-500">Model status unavailable</p>
		</div>
	{/if}
</Card>
