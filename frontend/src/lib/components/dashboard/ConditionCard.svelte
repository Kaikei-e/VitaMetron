<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import { vasToTextColor, vasToLabel } from '$lib/utils/condition';
	import { formatDateTime } from '$lib/utils/date';
	import type { ConditionLog } from '$lib/types/condition';

	let { condition }: { condition: ConditionLog | null } = $props();

	let scoreColor = $derived(condition ? vasToTextColor(condition.OverallVAS) : '');
	let label = $derived(condition ? vasToLabel(condition.OverallVAS) : '');
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Today's Condition</h3>
	{#if condition}
		<div class="mt-2 flex items-baseline gap-2">
			<span class="text-3xl font-bold {scoreColor}">{condition.OverallVAS}</span>
			<span class="text-sm text-gray-500 dark:text-gray-400">{label}</span>
		</div>
		<p class="mt-1 text-xs text-gray-400">{formatDateTime(condition.LoggedAt)}</p>
		{#if condition.Tags?.length}
			<div class="mt-2 flex flex-wrap gap-1">
				{#each condition.Tags as tag}
					<span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">{tag}</span>
				{/each}
			</div>
		{/if}
	{:else}
		<p class="mt-2 text-3xl font-bold text-gray-300 dark:text-gray-600">--</p>
		<p class="mt-1 text-xs text-gray-400">No data today</p>
	{/if}
</Card>
