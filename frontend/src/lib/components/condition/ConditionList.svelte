<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import { vasToTextColor, vasToBgColor, vasToLabel } from '$lib/utils/condition';
	import { formatFullDateTime, formatShortDate } from '$lib/utils/date';
	import type { ConditionLog } from '$lib/types/condition';

	let {
		conditions = [],
		total = 0,
		page = 1,
		limit = 20,
		ondelete
	}: {
		conditions?: ConditionLog[];
		total?: number;
		page?: number;
		limit?: number;
		ondelete?: (id: number) => void;
	} = $props();

	let deleting = $state<number | null>(null);

	async function handleDelete(id: number) {
		if (!ondelete) return;
		if (!confirm('Delete this condition log?')) return;
		deleting = id;
		try {
			ondelete(id);
		} finally {
			deleting = null;
		}
	}

	let totalPages = $derived(Math.max(1, Math.ceil(total / limit)));

	function formatVAS(v: number | null): string {
		return v !== null ? String(v) : '--';
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
					<th class="px-4 py-3 font-medium">Well-being</th>
					<th class="px-4 py-3 font-medium">Mood</th>
					<th class="px-4 py-3 font-medium">Energy</th>
					<th class="px-4 py-3 font-medium">Sleep</th>
					<th class="px-4 py-3 font-medium">Stress</th>
					<th class="px-4 py-3 font-medium">Tags</th>
					{#if ondelete}<th class="px-4 py-3 font-medium w-16"></th>{/if}
				</tr>
			</thead>
			<tbody>
				{#each conditions as cond, i}
					<tr class="border-b border-gray-100 dark:border-gray-800 {i % 2 === 1 ? 'bg-gray-50 dark:bg-gray-800/50' : ''}">
						<td class="px-4 py-3">{formatFullDateTime(cond.LoggedAt)}</td>
						<td class="px-4 py-3 font-bold {vasToTextColor(cond.OverallVAS)}">{cond.OverallVAS}</td>
						<td class="px-4 py-3 {vasToTextColor(cond.MoodVAS)}">{formatVAS(cond.MoodVAS)}</td>
						<td class="px-4 py-3 {vasToTextColor(cond.EnergyVAS)}">{formatVAS(cond.EnergyVAS)}</td>
						<td class="px-4 py-3 {vasToTextColor(cond.SleepQualityVAS)}">{formatVAS(cond.SleepQualityVAS)}</td>
						<td class="px-4 py-3 {vasToTextColor(cond.StressVAS)}">{formatVAS(cond.StressVAS)}</td>
						<td class="px-4 py-3">
							<div class="flex flex-wrap gap-1">
								{#each cond.Tags ?? [] as tag}
									<span class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">{tag}</span>
								{/each}
							</div>
						</td>
						{#if ondelete}
							<td class="px-4 py-3">
								<button
									onclick={() => handleDelete(cond.ID)}
									disabled={deleting === cond.ID}
									class="rounded p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
									title="Delete"
								>
									{#if deleting === cond.ID}
										<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4" stroke-linecap="round" class="opacity-75"/></svg>
									{:else}
										<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
									{/if}
								</button>
							</td>
						{/if}
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
					<div class="flex items-center gap-2">
						<span class="flex h-8 min-w-8 items-center justify-center rounded-full px-2 text-sm font-bold text-white {vasToBgColor(cond.OverallVAS)}">
							{cond.OverallVAS}
						</span>
						{#if ondelete}
							<button
								onclick={() => handleDelete(cond.ID)}
								disabled={deleting === cond.ID}
								class="rounded p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
								title="Delete"
							>
								{#if deleting === cond.ID}
									<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="4" stroke-linecap="round" class="opacity-75"/></svg>
								{:else}
									<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
								{/if}
							</button>
						{/if}
					</div>
				</div>
				{#if cond.MoodVAS !== null || cond.EnergyVAS !== null || cond.SleepQualityVAS !== null || cond.StressVAS !== null}
					<div class="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
						{#if cond.MoodVAS !== null}<span>Mood: <span class="{vasToTextColor(cond.MoodVAS)} font-medium">{cond.MoodVAS}</span></span>{/if}
						{#if cond.EnergyVAS !== null}<span>Energy: <span class="{vasToTextColor(cond.EnergyVAS)} font-medium">{cond.EnergyVAS}</span></span>{/if}
						{#if cond.SleepQualityVAS !== null}<span>Sleep: <span class="{vasToTextColor(cond.SleepQualityVAS)} font-medium">{cond.SleepQualityVAS}</span></span>{/if}
						{#if cond.StressVAS !== null}<span>Stress: <span class="{vasToTextColor(cond.StressVAS)} font-medium">{cond.StressVAS}</span></span>{/if}
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
