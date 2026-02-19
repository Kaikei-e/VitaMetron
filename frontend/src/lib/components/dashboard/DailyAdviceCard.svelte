<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import { regenerateAdvice } from '$lib/api/advice';
	import { simpleMarkdownToHtml } from '$lib/utils/markdown';
	import type { DailyAdvice } from '$lib/types/advice';

	let { advicePromise, effectiveDate }: { advicePromise: Promise<DailyAdvice | null>; effectiveDate: string } = $props();

	let currentAdvice = $state<DailyAdvice | null>(null);
	let regenerating = $state(false);
	let error = $state<string | null>(null);

	$effect(() => {
		advicePromise.then((a) => {
			currentAdvice = a;
		}).catch(() => {
			error = 'アドバイスの取得に失敗しました';
		});
	});

	async function handleRegenerate() {
		regenerating = true;
		error = null;
		try {
			currentAdvice = await regenerateAdvice(effectiveDate);
		} catch {
			error = 'アドバイスの再生成に失敗しました';
		} finally {
			regenerating = false;
		}
	}
</script>

<Card>
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-1.5">
			<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">今日の一言</h3>
			<HelpTooltip text="あなたのバイオメトリクスデータとMLモデルの出力をもとに、AIが生成したパーソナルヘルスアドバイスです。医学的な診断ではありません。" />
		</div>
		<button
			type="button"
			class="text-xs px-2 py-1 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			disabled={regenerating}
			onclick={handleRegenerate}
		>
			{regenerating ? '生成中...' : '再生成'}
		</button>
	</div>

	{#await advicePromise}
		<!-- Loading skeleton -->
		<div class="mt-3 space-y-2 animate-pulse">
			<div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
			<div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
			<div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/6"></div>
		</div>
	{:then}
		{#if error}
			<p class="mt-3 text-sm text-red-400">{error}</p>
		{:else if currentAdvice}
			<div class="advice-content mt-3 text-sm leading-relaxed text-gray-700 dark:text-gray-200">
				{@html simpleMarkdownToHtml(currentAdvice.AdviceText)}
			</div>
			<div class="mt-2 flex items-center gap-3 text-xs text-gray-500">
				<span>{currentAdvice.ModelName}</span>
				{#if currentAdvice.GenerationMs != null}
					<span>{(currentAdvice.GenerationMs / 1000).toFixed(1)}s</span>
				{/if}
				{#if currentAdvice.Cached}
					<span class="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">cached</span>
				{/if}
			</div>
		{:else}
			<p class="mt-3 text-sm text-gray-400">本日のデータがまだ不十分です</p>
		{/if}
	{:catch}
		<p class="mt-3 text-sm text-red-400">アドバイスの取得に失敗しました</p>
	{/await}
</Card>

<style>
	.advice-content :global(h4) {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-gray-700);
		margin-top: 0.75rem;
		margin-bottom: 0.25rem;
	}

	@media (prefers-color-scheme: dark) {
		.advice-content :global(h4) {
			color: var(--color-gray-300);
		}
	}

	.advice-content :global(h4:first-child) {
		margin-top: 0;
	}

	.advice-content :global(strong) {
		font-weight: 600;
		color: var(--color-gray-800);
	}

	@media (prefers-color-scheme: dark) {
		.advice-content :global(strong) {
			color: var(--color-gray-200);
		}
	}

	.advice-content :global(p) {
		margin-bottom: 0.5rem;
	}

	.advice-content :global(p:last-child) {
		margin-bottom: 0;
	}

	.advice-content :global(ul) {
		list-style-type: disc;
		padding-left: 1.25rem;
		margin-bottom: 0.5rem;
	}

	.advice-content :global(li) {
		margin-bottom: 0.125rem;
	}
</style>
