<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import type { ConditionLog } from '$lib/types/condition';

	let { condition }: { condition: ConditionLog | null } = $props();

	const colorMap: Record<number, string> = {
		1: 'text-condition-1',
		2: 'text-condition-2',
		3: 'text-condition-3',
		4: 'text-condition-4',
		5: 'text-condition-5'
	};

	let scoreColor = $derived(condition ? colorMap[condition.Overall] ?? '' : '');

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleString('ja-JP', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
	}
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Today's Condition</h3>
	{#if condition}
		<p class="mt-2 text-3xl font-bold {scoreColor}">{condition.Overall}</p>
		<p class="mt-1 text-xs text-gray-400">{formatDate(condition.LoggedAt)}</p>
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
