<script lang="ts">
	import { syncNow as performSync, getFitbitAuthUrl, disconnectFitbit as performDisconnect } from '$lib/api/sync';
	import Badge from '$lib/components/ui/Badge.svelte';

	let {
		connected = false,
		fitbitResult = null
	}: {
		connected?: boolean;
		fitbitResult?: string | null;
	} = $props();

	let fitbitConnected = $state(false);
	let loading = $state(false);
	let syncing = $state(false);
	let syncDate = $state(new Date().toISOString().slice(0, 10));
	let toast = $state<{ message: string; variant: 'success' | 'error' } | null>(null);

	$effect(() => {
		fitbitConnected = connected;
		if (fitbitResult === 'connected') {
			fitbitConnected = true;
			toast = { message: 'Fitbit connected successfully!', variant: 'success' };
		} else if (fitbitResult === 'error') {
			toast = { message: 'Failed to connect Fitbit. Please try again.', variant: 'error' };
		}
	});

	async function connectFitbit() {
		loading = true;
		try {
			const url = await getFitbitAuthUrl();
			window.location.href = url;
		} catch {
			toast = { message: 'Failed to start Fitbit authorization.', variant: 'error' };
			loading = false;
		}
	}

	async function disconnectFitbit() {
		loading = true;
		try {
			await performDisconnect();
			fitbitConnected = false;
			toast = { message: 'Fitbit disconnected.', variant: 'success' };
		} catch {
			toast = { message: 'Failed to disconnect Fitbit.', variant: 'error' };
		} finally {
			loading = false;
		}
	}

	async function syncNow() {
		syncing = true;
		try {
			await performSync(syncDate);
			toast = { message: `Sync completed for ${syncDate}!`, variant: 'success' };
		} catch {
			toast = { message: 'Sync failed. Please try again.', variant: 'error' };
		} finally {
			syncing = false;
		}
	}

	function dismissToast() {
		toast = null;
	}
</script>

{#if toast}
	<div
		class="mb-4 flex items-center justify-between rounded-lg px-4 py-3 {toast.variant === 'success'
			? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
			: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200'}"
		role="alert"
	>
		<span>{toast.message}</span>
		<button onclick={dismissToast} class="ml-4 text-sm font-medium underline">Dismiss</button>
	</div>
{/if}

<section class="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
	<div class="flex items-center gap-3 mb-4">
		<h2 class="text-lg font-semibold">Fitbit Integration</h2>
		{#if fitbitConnected}
			<Badge text="Connected" variant="success" />
		{:else}
			<Badge text="Disconnected" />
		{/if}
	</div>
	<p class="text-gray-600 dark:text-gray-400 mb-4">Connect your Fitbit account to sync biometric data.</p>
	{#if fitbitConnected}
		<button
			onclick={disconnectFitbit}
			disabled={loading}
			class="min-h-12 rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:opacity-50"
		>
			{loading ? 'Disconnecting...' : 'Disconnect Fitbit'}
		</button>
	{:else}
		<button
			onclick={connectFitbit}
			disabled={loading}
			class="min-h-12 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
		>
			{loading ? 'Connecting...' : 'Connect Fitbit'}
		</button>
	{/if}
</section>

{#if fitbitConnected}
	<section class="mt-6 rounded-lg bg-white p-6 shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
		<h2 class="text-lg font-semibold mb-4">Manual Sync</h2>
		<p class="text-gray-600 dark:text-gray-400 mb-4">Sync biometric data for a specific date.</p>
		<div class="flex items-end gap-3">
			<label class="flex flex-col gap-1">
				<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Date</span>
				<input
					type="date"
					bind:value={syncDate}
					class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
				/>
			</label>
			<button
				onclick={syncNow}
				disabled={syncing}
				class="min-h-12 rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50"
			>
				{syncing ? 'Syncing...' : 'Sync Now'}
			</button>
		</div>
	</section>
{/if}
