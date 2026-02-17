<script lang="ts">
	import { apiFetch } from '$lib/api';
	import Badge from '$lib/components/ui/Badge.svelte';

	let { data } = $props();

	let fitbitConnected = $state(data.fitbitConnected);
	let loading = $state(false);
	let toast: { message: string; variant: 'success' | 'error' } | null = $state(null);

	if (data.fitbitResult === 'connected') {
		fitbitConnected = true;
		toast = { message: 'Fitbit connected successfully!', variant: 'success' };
	} else if (data.fitbitResult === 'error') {
		toast = { message: 'Failed to connect Fitbit. Please try again.', variant: 'error' };
	}

	async function connectFitbit() {
		loading = true;
		try {
			const res = await apiFetch('/api/auth/fitbit');
			const { url }: { url: string } = await res.json();
			window.location.href = url;
		} catch {
			toast = { message: 'Failed to start Fitbit authorization.', variant: 'error' };
			loading = false;
		}
	}

	let syncing = $state(false);
	let syncDate = $state(new Date().toISOString().slice(0, 10));

	async function syncNow() {
		syncing = true;
		try {
			const res = await apiFetch(`/api/sync?date=${syncDate}`, { method: 'POST' });
			if (!res.ok) throw new Error();
			toast = { message: `Sync completed for ${syncDate}!`, variant: 'success' };
		} catch {
			toast = { message: 'Sync failed. Please try again.', variant: 'error' };
		} finally {
			syncing = false;
		}
	}

	async function disconnectFitbit() {
		loading = true;
		try {
			await apiFetch('/api/auth/fitbit', { method: 'DELETE' });
			fitbitConnected = false;
			toast = { message: 'Fitbit disconnected.', variant: 'success' };
		} catch {
			toast = { message: 'Failed to disconnect Fitbit.', variant: 'error' };
		} finally {
			loading = false;
		}
	}

	let hcFiles: FileList | null = $state(null);
	let importing = $state(false);
	let importResult: {
		dates_imported: number;
		hr_samples: number;
		sleep_stages: number;
		exercise_logs: number;
	} | null = $state(null);

	async function importHealthConnect() {
		if (!hcFiles?.length) return;
		importing = true;
		importResult = null;
		try {
			const formData = new FormData();
			formData.append('file', hcFiles[0]);
			const res = await fetch('/api/import/health-connect', {
				method: 'POST',
				body: formData
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || 'Import failed');
			}
			importResult = await res.json();
			toast = { message: 'Health Connect import completed!', variant: 'success' };
		} catch (e) {
			toast = {
				message: e instanceof Error ? e.message : 'Import failed. Please try again.',
				variant: 'error'
			};
		} finally {
			importing = false;
		}
	}

	// ── Apple Watch (HealthKit) Import ──
	let hkFiles: FileList | null = $state(null);
	let hkImporting = $state(false);
	let hkUploadProgress = $state(0);
	let hkProcessStage = $state('');
	let hkProcessProgress: {
		status: string;
		stage: string;
		records_processed: number;
		records_total: number;
		days_written: number;
		current_date: string;
		errors: string[];
		result?: {
			days_written: number;
			hr_samples: number;
			sleep_stages: number;
			exercise_logs: number;
		};
	} | null = $state(null);
	let hkResult: {
		days_written: number;
		hr_samples: number;
		sleep_stages: number;
		exercise_logs: number;
	} | null = $state(null);

	async function importHealthKit() {
		if (!hkFiles?.length) return;
		hkImporting = true;
		hkUploadProgress = 0;
		hkProcessStage = 'uploading';
		hkProcessProgress = null;
		hkResult = null;

		try {
			// Stage 1: Upload with XHR for progress
			const jobId = await uploadHealthKit(hkFiles[0]);

			// Stage 2: Stream processing progress via SSE
			hkProcessStage = 'processing';
			await streamProgress(jobId);
		} catch (e) {
			toast = {
				message: e instanceof Error ? e.message : 'HealthKit import failed.',
				variant: 'error'
			};
		} finally {
			hkImporting = false;
		}
	}

	const CHUNK_SIZE = 80 * 1024 * 1024; // 80MB — under Cloudflare Tunnel 100MB limit

	async function uploadHealthKit(file: File): Promise<string> {
		const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

		// 1. Init upload session
		const initRes = await fetch('/api/import/healthkit/init', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				file_name: file.name,
				file_size: file.size,
				chunk_size: CHUNK_SIZE
			})
		});
		if (!initRes.ok) {
			const err = await initRes.json();
			throw new Error(err.error || 'Failed to init upload');
		}
		const { upload_id } = await initRes.json();

		// 2. Upload chunks sequentially
		for (let i = 0; i < totalChunks; i++) {
			const start = i * CHUNK_SIZE;
			const end = Math.min(start + CHUNK_SIZE, file.size);
			const chunk = file.slice(start, end);

			const res = await fetch(`/api/import/healthkit/chunk/${upload_id}/${i}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/octet-stream' },
				body: chunk
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.error || `Chunk ${i} upload failed`);
			}

			hkUploadProgress = Math.round(((i + 1) / totalChunks) * 100);
		}

		// 3. Complete — triggers server-side concatenation + processing
		const completeRes = await fetch(`/api/import/healthkit/complete/${upload_id}`, {
			method: 'POST'
		});
		if (!completeRes.ok) {
			const err = await completeRes.json();
			throw new Error(err.error || 'Failed to complete upload');
		}
		const { job_id } = await completeRes.json();
		return job_id;
	}

	function streamProgress(jobId: string): Promise<void> {
		return new Promise((resolve, reject) => {
			const es = new EventSource(`/api/import/healthkit/stream/${jobId}`);

			es.onmessage = (event) => {
				try {
					const data = JSON.parse(event.data);
					hkProcessProgress = data;

					if (data.status === 'completed') {
						es.close();
						hkResult = data.result || null;
						toast = { message: 'Apple Watch import completed!', variant: 'success' };
						resolve();
					} else if (data.status === 'failed') {
						es.close();
						const errMsg = data.errors?.join(', ') || 'Processing failed';
						reject(new Error(errMsg));
					}
				} catch {
					// ignore parse errors
				}
			};

			es.onerror = () => {
				es.close();
				// Try to get final status via polling
				fetch(`/api/import/healthkit/status/${jobId}`)
					.then((r) => r.json())
					.then((data) => {
						if (data.status === 'completed') {
							hkResult = data.result || null;
							toast = { message: 'Apple Watch import completed!', variant: 'success' };
							resolve();
						} else {
							reject(new Error('Connection lost during processing'));
						}
					})
					.catch(() => reject(new Error('Connection lost during processing')));
			};
		});
	}

	function dismissToast() {
		toast = null;
	}
</script>

<svelte:head>
	<title>Settings — VitaMetron</title>
</svelte:head>

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

<h1 class="text-2xl font-bold mb-6">Settings</h1>

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
			{loading ? 'Disconnecting…' : 'Disconnect Fitbit'}
		</button>
	{:else}
		<button
			onclick={connectFitbit}
			disabled={loading}
			class="min-h-12 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
		>
			{loading ? 'Connecting…' : 'Connect Fitbit'}
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
				{syncing ? 'Syncing…' : 'Sync Now'}
			</button>
		</div>
	</section>
{/if}

<section class="mt-6 rounded-lg bg-white p-6 shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
	<h2 class="text-lg font-semibold mb-4">Health Connect Import</h2>
	<p class="text-gray-600 dark:text-gray-400 mb-4">
		Health Connect エクスポート (.zip) をアップロードしてデータを取り込みます。
	</p>
	<div class="flex items-end gap-3">
		<label class="flex flex-col gap-1 min-w-0 flex-1">
			<span class="text-sm font-medium text-gray-700 dark:text-gray-300">File</span>
			<input
				type="file"
				accept=".zip"
				bind:files={hcFiles}
				class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
			/>
		</label>
		<button
			onclick={importHealthConnect}
			disabled={importing || !hcFiles?.length}
			class="min-h-12 rounded-lg bg-purple-600 px-4 py-2 text-white hover:bg-purple-700 disabled:opacity-50"
		>
			{importing ? 'Importing…' : 'Import'}
		</button>
	</div>
	{#if importResult}
		<div class="mt-3 text-sm text-gray-600 dark:text-gray-400">
			{importResult.dates_imported} 日分 / HR {importResult.hr_samples} 件 /
			Sleep {importResult.sleep_stages} 件 / Exercise {importResult.exercise_logs} 件
		</div>
	{/if}
</section>

<section class="mt-6 rounded-lg bg-white p-6 shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
	<h2 class="text-lg font-semibold mb-4">Apple Watch Import</h2>
	<p class="text-gray-600 dark:text-gray-400 mb-4">
		HealthKit エクスポート (.zip) をアップロードして Apple Watch データを取り込みます。
	</p>
	<div class="flex items-end gap-3">
		<label class="flex flex-col gap-1 min-w-0 flex-1">
			<span class="text-sm font-medium text-gray-700 dark:text-gray-300">File</span>
			<input
				type="file"
				accept=".zip"
				bind:files={hkFiles}
				disabled={hkImporting}
				class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
			/>
		</label>
		<button
			onclick={importHealthKit}
			disabled={hkImporting || !hkFiles?.length}
			class="min-h-12 rounded-lg bg-orange-600 px-4 py-2 text-white hover:bg-orange-700 disabled:opacity-50"
		>
			{hkImporting ? 'Importing…' : 'Import'}
		</button>
	</div>

	{#if hkImporting}
		<div class="mt-4 space-y-2">
			{#if hkProcessStage === 'uploading'}
				<div class="text-sm text-gray-600 dark:text-gray-400">Uploading… {hkUploadProgress}%</div>
				<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-2 rounded-full bg-orange-500 transition-all"
						style="width: {hkUploadProgress}%"
					></div>
				</div>
			{:else if hkProcessProgress}
				{@const pct = hkProcessProgress.records_total > 0
					? Math.round((hkProcessProgress.records_processed / hkProcessProgress.records_total) * 100)
					: 0}
				<div class="text-sm text-gray-600 dark:text-gray-400">
					Processing: {hkProcessProgress.current_date}
					({hkProcessProgress.days_written} 日) — {pct}%
				</div>
				<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-2 rounded-full bg-orange-500 transition-all"
						style="width: {pct}%"
					></div>
				</div>
				{#if hkProcessProgress.errors.length > 0}
					<div class="text-xs text-red-500 dark:text-red-400">
						{hkProcessProgress.errors.length} error(s)
					</div>
				{/if}
			{/if}
		</div>
	{/if}

	{#if hkResult}
		<div class="mt-3 text-sm text-gray-600 dark:text-gray-400">
			{hkResult.days_written} 日分 / HR {hkResult.hr_samples.toLocaleString()} 件 /
			Sleep {hkResult.sleep_stages.toLocaleString()} 件 / Workout {hkResult.exercise_logs.toLocaleString()} 件
		</div>
	{/if}
</section>
