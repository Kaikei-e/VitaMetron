<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import { syncNow as performSync } from '$lib/api/sync';
	import { formatDateTime } from '$lib/utils/date';
	import type { DailySummary } from '$lib/types/biometrics';

	let { summary }: { summary: DailySummary | null } = $props();

	let syncing = $state(false);
	let toast = $state<{ message: string; variant: 'success' | 'error' } | null>(null);

	async function syncNow() {
		syncing = true;
		toast = null;
		try {
			await performSync();
			toast = { message: 'Sync completed!', variant: 'success' };
		} catch {
			toast = { message: 'Sync failed.', variant: 'error' };
		} finally {
			syncing = false;
		}
	}
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Sync Status</h3>

	{#if toast}
		<p
			class="mb-2 rounded px-2 py-1 text-xs {toast.variant === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-200' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200'}"
			role="alert"
		>
			{toast.message}
		</p>
	{/if}

	{#if summary}
		<p class="text-sm text-gray-600 dark:text-gray-300">
			Last synced: <span class="font-medium">{formatDateTime(summary.SyncedAt)}</span>
		</p>
		<p class="mt-1 text-xs text-gray-400">Provider: {summary.Provider}</p>
	{:else}
		<p class="text-gray-400">No data synced yet</p>
	{/if}

	<button
		onclick={syncNow}
		disabled={syncing}
		class="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
	>
		{syncing ? 'Syncing...' : 'Sync Now'}
	</button>
</Card>
