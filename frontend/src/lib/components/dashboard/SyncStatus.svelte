<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import { apiFetch } from '$lib/api';
	import type { DailySummary } from '$lib/types/biometrics';

	let { summary }: { summary: DailySummary | null } = $props();

	let syncing = $state(false);
	let toast = $state<{ message: string; variant: 'success' | 'error' } | null>(null);

	function formatSyncedAt(iso: string): string {
		return new Date(iso).toLocaleString('ja-JP', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function syncNow() {
		syncing = true;
		toast = null;
		try {
			const res = await apiFetch('/api/sync', { method: 'POST' });
			if (!res.ok) throw new Error();
			toast = { message: 'Sync completed!', variant: 'success' };
		} catch {
			toast = { message: 'Sync failed.', variant: 'error' };
		} finally {
			syncing = false;
		}
	}
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 mb-2">Sync Status</h3>

	{#if toast}
		<p
			class="mb-2 rounded px-2 py-1 text-xs {toast.variant === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}"
			role="alert"
		>
			{toast.message}
		</p>
	{/if}

	{#if summary}
		<p class="text-sm text-gray-600">
			Last synced: <span class="font-medium">{formatSyncedAt(summary.SyncedAt)}</span>
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
