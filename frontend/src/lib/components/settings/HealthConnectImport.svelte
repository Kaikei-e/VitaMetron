<script lang="ts">
	import { chunkedUpload } from '$lib/utils/chunked-upload';
	import { streamProgress } from '$lib/utils/stream-progress';

	interface HCProgress {
		status: string;
		stage: string;
		error?: string;
		result?: HCResult;
	}

	interface HCResult {
		dates_imported: number;
		hr_samples: number;
		sleep_stages: number;
		exercise_logs: number;
	}

	let hcFiles: FileList | null = $state(null);
	let importing = $state(false);
	let uploadProgress = $state(0);
	let processStage: 'uploading' | 'processing' = $state('uploading');
	let processProgress: HCProgress | null = $state(null);
	let importResult: HCResult | null = $state(null);
	let toast = $state<{ message: string; variant: 'success' | 'error' } | null>(null);

	async function importHealthConnect() {
		if (!hcFiles?.length) return;
		importing = true;
		uploadProgress = 0;
		processStage = 'uploading';
		processProgress = null;
		importResult = null;

		try {
			const jobId = await chunkedUpload({
				file: hcFiles[0],
				initUrl: '/api/import/health-connect/init',
				chunkUrl: (id, i) => `/api/import/health-connect/chunk/${id}/${i}`,
				completeUrl: (id) => `/api/import/health-connect/complete/${id}`,
				onProgress: (pct) => (uploadProgress = pct)
			});

			processStage = 'processing';

			const streamResult = await streamProgress<HCProgress>({
				streamUrl: `/api/import/health-connect/stream/${jobId}`,
				statusUrl: `/api/import/health-connect/status/${jobId}`,
				onProgress: (data) => (processProgress = data),
				isCompleted: (data) => data.status === 'completed',
				isFailed: (data) => data.status === 'failed',
				getError: (data) => data.error || 'Processing failed',
				getResult: (data) => data.result || null
			});

			importResult = (streamResult as HCResult) || null;
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
</script>

<section class="mt-6 rounded-lg bg-white p-6 shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
	<h2 class="text-lg font-semibold mb-4">Health Connect Import</h2>
	<p class="text-gray-600 dark:text-gray-400 mb-4">
		Health Connect エクスポート (.zip) をアップロードしてデータを取り込みます。
	</p>

	{#if toast}
		<div
			class="mb-4 flex items-center justify-between rounded-lg px-4 py-3 {toast.variant === 'success'
				? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
				: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200'}"
			role="alert"
		>
			<span>{toast.message}</span>
			<button onclick={() => (toast = null)} class="ml-4 text-sm font-medium underline">Dismiss</button>
		</div>
	{/if}

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
			{importing ? 'Importing...' : 'Import'}
		</button>
	</div>
	{#if importing}
		<div class="mt-4 space-y-2">
			{#if processStage === 'uploading'}
				<div class="text-sm text-gray-600 dark:text-gray-400">Uploading... {uploadProgress}%</div>
				<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-2 rounded-full bg-purple-500 transition-all"
						style="width: {uploadProgress}%"
					></div>
				</div>
			{:else if processProgress}
				<div class="text-sm text-gray-600 dark:text-gray-400">
					Processing: {processProgress.stage === 'extracting' ? 'Extracting DB from ZIP...' : 'Importing data...'}
				</div>
				<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div class="h-2 rounded-full bg-purple-500 animate-pulse" style="width: 100%"></div>
				</div>
			{:else}
				<div class="text-sm text-gray-600 dark:text-gray-400">Starting processing...</div>
				<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div class="h-2 rounded-full bg-purple-500 animate-pulse" style="width: 100%"></div>
				</div>
			{/if}
		</div>
	{/if}
	{#if importResult}
		<div class="mt-3 text-sm text-gray-600 dark:text-gray-400">
			{importResult.dates_imported} 日分 / HR {importResult.hr_samples} 件 /
			Sleep {importResult.sleep_stages} 件 / Exercise {importResult.exercise_logs} 件
		</div>
	{/if}
</section>
