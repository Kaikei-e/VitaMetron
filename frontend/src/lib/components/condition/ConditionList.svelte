<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import type { ConditionLog } from '$lib/types/condition';

	let {
		conditions = [],
		total = 0,
		page = 1,
		limit = 20
	}: {
		conditions?: ConditionLog[];
		total?: number;
		page?: number;
		limit?: number;
	} = $props();

	let totalPages = $derived(Math.max(1, Math.ceil(total / limit)));

	const scoreColor: Record<number, string> = {
		1: 'text-condition-1',
		2: 'text-condition-2',
		3: 'text-condition-3',
		4: 'text-condition-4',
		5: 'text-condition-5'
	};

	const scoreBg: Record<number, string> = {
		1: 'bg-condition-1',
		2: 'bg-condition-2',
		3: 'bg-condition-3',
		4: 'bg-condition-4',
		5: 'bg-condition-5'
	};

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('ja-JP', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatShortDate(iso: string): string {
		return new Date(iso).toLocaleDateString('ja-JP', {
			month: 'short',
			day: 'numeric'
		});
	}
</script>

{#if conditions.length === 0}
	<Card>
		<p class="text-gray-400">No condition logs recorded yet.</p>
	</Card>
{:else}
	<!-- Desktop: Table view -->
	<div class="hidden lg:block overflow-x-auto rounded-lg bg-white shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-gray-200 text-left text-gray-500 dark:border-gray-700 dark:text-gray-400">
					<th class="px-4 py-3 font-medium">Date</th>
					<th class="px-4 py-3 font-medium">Overall</th>
					<th class="px-4 py-3 font-medium">Mental</th>
					<th class="px-4 py-3 font-medium">Physical</th>
					<th class="px-4 py-3 font-medium">Energy</th>
					<th class="px-4 py-3 font-medium">Tags</th>
				</tr>
			</thead>
			<tbody>
				{#each conditions as cond, i}
					<tr class="border-b border-gray-100 dark:border-gray-800 {i % 2 === 1 ? 'bg-gray-50 dark:bg-gray-800/50' : ''}">
						<td class="px-4 py-3">{formatDate(cond.LoggedAt)}</td>
						<td class="px-4 py-3 font-bold {scoreColor[cond.Overall] ?? ''}">{cond.Overall}</td>
						<td class="px-4 py-3">{cond.Mental ?? '--'}</td>
						<td class="px-4 py-3">{cond.Physical ?? '--'}</td>
						<td class="px-4 py-3">{cond.Energy ?? '--'}</td>
						<td class="px-4 py-3">
							<div class="flex flex-wrap gap-1">
								{#each cond.Tags ?? [] as tag}
									<span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">{tag}</span>
								{/each}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	<!-- Mobile: Card list -->
	<div class="lg:hidden flex flex-col gap-3">
		{#each conditions as cond}
			<Card>
				<div class="flex items-center justify-between">
					<span class="text-sm text-gray-500">{formatShortDate(cond.LoggedAt)}</span>
					<span class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white {scoreBg[cond.Overall] ?? 'bg-gray-400'}">
						{cond.Overall}
					</span>
				</div>
				{#if cond.Mental !== null || cond.Physical !== null || cond.Energy !== null}
					<div class="mt-2 flex gap-3 text-xs text-gray-500">
						{#if cond.Mental !== null}<span>Mental: {cond.Mental}</span>{/if}
						{#if cond.Physical !== null}<span>Physical: {cond.Physical}</span>{/if}
						{#if cond.Energy !== null}<span>Energy: {cond.Energy}</span>{/if}
					</div>
				{/if}
				{#if cond.Tags?.length}
					<div class="mt-2 flex flex-wrap gap-1">
						{#each cond.Tags as tag}
							<span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">{tag}</span>
						{/each}
					</div>
				{/if}
			</Card>
		{/each}
	</div>
{/if}

<!-- Pagination -->
{#if totalPages > 1}
	<div class="mt-4 flex items-center justify-center gap-4">
		{#if page > 1}
			<a
				href="?page={page - 1}"
				class="min-h-12 inline-flex items-center rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
			>
				Previous
			</a>
		{/if}
		<span class="text-sm text-gray-500">Page {page} of {totalPages}</span>
		{#if page < totalPages}
			<a
				href="?page={page + 1}"
				class="min-h-12 inline-flex items-center rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
			>
				Next
			</a>
		{/if}
	</div>
{/if}
