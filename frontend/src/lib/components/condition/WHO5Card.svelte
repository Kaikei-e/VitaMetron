<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import type { WHO5Assessment } from '$lib/types/who5';

	let { latest }: { latest: WHO5Assessment | null } = $props();

	let alertLevel = $derived.by(() => {
		if (!latest) return 'none';
		if (latest.Percentage <= 28) return 'warning';
		if (latest.Percentage <= 50) return 'caution';
		return 'normal';
	});

	let daysSince = $derived.by(() => {
		if (!latest) return null;
		const assessed = new Date(latest.AssessedAt);
		const now = new Date();
		return Math.floor((now.getTime() - assessed.getTime()) / (1000 * 60 * 60 * 24));
	});

	let needsNew = $derived(daysSince !== null && daysSince >= 14);
</script>

<Card>
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">WHO-5 Well-Being</h3>
		<a
			href="/conditions/who5"
			class="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
		>
			{latest ? 'New Assessment' : 'Take Assessment'}
		</a>
	</div>

	{#if latest}
		<div class="mt-3 flex items-baseline gap-2">
			<span class="text-3xl font-bold
				{alertLevel === 'warning' ? 'text-red-600' :
				 alertLevel === 'caution' ? 'text-yellow-600' :
				 'text-green-600'}">
				{latest.Percentage}%
			</span>
			<span class="text-sm text-gray-500 dark:text-gray-400">
				({latest.RawScore}/25)
			</span>
		</div>

		{#if alertLevel === 'warning'}
			<p class="mt-1 text-xs text-red-600 dark:text-red-400">Low well-being — consider professional support</p>
		{:else if alertLevel === 'caution'}
			<p class="mt-1 text-xs text-yellow-600 dark:text-yellow-400">Below average well-being</p>
		{/if}

		{#if needsNew}
			<p class="mt-2 rounded bg-blue-50 dark:bg-blue-900/20 px-2 py-1 text-xs text-blue-700 dark:text-blue-300">
				{daysSince}日経過 — 新しい評価を記録しましょう
			</p>
		{:else}
			<p class="mt-2 text-xs text-gray-400">{daysSince}日前に記録</p>
		{/if}
	{:else}
		<p class="mt-3 text-sm text-gray-400">No assessments yet</p>
		<p class="mt-1 text-xs text-gray-400">
			WHO-5 is a validated well-being questionnaire (5 items, ~1 min)
		</p>
	{/if}
</Card>
