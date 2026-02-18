<script lang="ts">
	import { chunkedUpload } from '$lib/utils/chunked-upload';
	import { streamProgress } from '$lib/utils/stream-progress';

	interface HKResult {
		days_written: number;
		hr_samples: number;
		sleep_stages: number;
		exercise_logs: number;
	}

	interface HKProgress {
		status: string;
		stage: string;
		records_processed: number;
		records_total: number;
		days_written: number;
		current_date: string;
		errors: string[];
		result?: HKResult;
	}

	let hkFiles: FileList | null = $state(null);
	let importing = $state(false);
	let uploadProgress = $state(0);
	let processStage = $state('');
	let processProgress: HKProgress | null = $state(null);
	let result: HKResult | null = $state(null);
	let toast = $state<{ message: string; variant: 'success' | 'error' } | null>(null);

	async function importHealthKit() {
		if (!hkFiles?.length) return;
		importing = true;
		uploadProgress = 0;
		processStage = 'uploading';
		processProgress = null;
		result = null;

		try {
			const jobId = await chunkedUpload({
				file: hkFiles[0],
				initUrl: '/api/import/healthkit/init',
				chunkUrl: (id, i) => `/api/import/healthkit/chunk/${id}/${i}`,
				completeUrl: (id) => `/api/import/healthkit/complete/${id}`,
				onProgress: (pct) => (uploadProgress = pct)
			});

			processStage = 'processing';

			const streamResult = await streamProgress<HKProgress>({
				streamUrl: `/api/import/healthkit/stream/${jobId}`,
				statusUrl: `/api/import/healthkit/status/${jobId}`,
				onProgress: (data) => (processProgress = data),
				isCompleted: (data) => data.status === 'completed',
				isFailed: (data) => data.status === 'failed',
				getError: (data) => data.errors?.join(', ') || 'Processing failed',
				getResult: (data) => data.result || null
			});

			result = (streamResult as HKResult) || null;
			toast = { message: 'Apple Watch import completed!', variant: 'success' };
		} catch (e) {
			toast = {
				message: e instanceof Error ? e.message : 'HealthKit import failed.',
				variant: 'error'
			};
		} finally {
			importing = false;
		}
	}
</script>

<section class="mt-6 rounded-lg bg-white p-6 shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
	<h2 class="text-lg font-semibold mb-4">Apple Watch Import</h2>
	<p class="text-gray-600 dark:text-gray-400 mb-4">
		HealthKit エクスポート (.zip) をアップロードして Apple Watch データを取り込みます。
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
				bind:files={hkFiles}
				disabled={importing}
				class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
			/>
		</label>
		<button
			onclick={importHealthKit}
			disabled={importing || !hkFiles?.length}
			class="min-h-12 rounded-lg bg-orange-600 px-4 py-2 text-white hover:bg-orange-700 disabled:opacity-50"
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
						class="h-2 rounded-full bg-orange-500 transition-all"
						style="width: {uploadProgress}%"
					></div>
				</div>
			{:else if processProgress}
				{@const pct = processProgress.records_total > 0
					? Math.round((processProgress.records_processed / processProgress.records_total) * 100)
					: 0}
				<div class="text-sm text-gray-600 dark:text-gray-400">
					Processing: {processProgress.current_date}
					({processProgress.days_written} 日) — {pct}%
				</div>
				<div class="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
					<div
						class="h-2 rounded-full bg-orange-500 transition-all"
						style="width: {pct}%"
					></div>
				</div>
				{#if processProgress.errors.length > 0}
					<div class="text-xs text-red-500 dark:text-red-400">
						{processProgress.errors.length} error(s)
					</div>
				{/if}
			{/if}
		</div>
	{/if}

	{#if result}
		<div class="mt-3 text-sm text-gray-600 dark:text-gray-400">
			{result.days_written} 日分 / HR {result.hr_samples.toLocaleString()} 件 /
			Sleep {result.sleep_stages.toLocaleString()} 件 / Workout {result.exercise_logs.toLocaleString()} 件
		</div>
	{/if}
</section>
