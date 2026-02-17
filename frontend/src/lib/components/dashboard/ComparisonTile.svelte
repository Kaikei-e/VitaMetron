<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import type { MetricComparison } from '$lib/types/biometrics';

	let { comparison }: { comparison: MetricComparison } = $props();

	let deltaColor = $derived.by(() => {
		if (comparison.delta == null || comparison.delta === 0) return 'text-gray-400';
		const positive = comparison.delta > 0;
		const good = comparison.higherIsBetter ? positive : !positive;
		return good
			? 'text-green-600 dark:text-green-400'
			: 'text-red-500 dark:text-red-400';
	});

	let arrow = $derived.by(() => {
		if (comparison.delta == null || comparison.delta === 0) return '';
		return comparison.delta > 0 ? '\u2191' : '\u2193';
	});

	function fmt(v: number | null): string {
		if (v == null) return '--';
		return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(1);
	}
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">{comparison.label}</h3>
	<p class="mt-2 text-2xl font-bold">
		{fmt(comparison.today)}
		{#if comparison.unit}
			<span class="ml-1 text-sm font-normal text-gray-400">{comparison.unit}</span>
		{/if}
	</p>
	{#if comparison.delta != null}
		<p class="mt-1 text-sm {deltaColor}">
			{arrow}
			{Math.abs(comparison.delta).toFixed(1)}
			<span class="text-xs text-gray-400 ml-1">vs yesterday ({fmt(comparison.yesterday)})</span>
		</p>
	{:else}
		<p class="mt-1 text-xs text-gray-400">No comparison data</p>
	{/if}
</Card>
