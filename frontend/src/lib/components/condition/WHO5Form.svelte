<script lang="ts">
	import { goto } from '$app/navigation';
	import { createWHO5 } from '$lib/api/who5';
	import Card from '$lib/components/ui/Card.svelte';

	const ITEMS = [
		'明るく楽しい気分で過ごした',
		'落ち着いてリラックスした気分で過ごした',
		'活動的で元気に過ごした',
		'目覚めた時に十分な休養感があった',
		'日常生活に興味のあることがたくさんあった'
	];

	const SCALE_LABELS = [
		'まったくない',
		'ほんの少し',
		'半分以下',
		'半分以上',
		'ほとんど',
		'いつも'
	];

	let items = $state<(number | null)[]>([null, null, null, null, null]);
	let note = $state('');
	let submitting = $state(false);
	let error = $state('');

	let allAnswered = $derived(items.every((v) => v !== null));
	let rawScore = $derived(
		allAnswered ? items.reduce<number>((sum, v) => sum + (v ?? 0), 0) : null
	);
	let percentage = $derived(rawScore !== null ? rawScore * 4 : null);

	let alertLevel = $derived.by(() => {
		if (percentage === null) return 'none';
		if (percentage <= 28) return 'warning';
		if (percentage <= 50) return 'caution';
		return 'normal';
	});

	function formatLocalDate(d: Date): string {
		return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
	}

	function getPeriodDates() {
		const end = new Date();
		const start = new Date();
		start.setDate(end.getDate() - 14);
		return {
			start: formatLocalDate(start),
			end: formatLocalDate(end)
		};
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!allAnswered || submitting) return;

		error = '';
		submitting = true;

		const period = getPeriodDates();

		try {
			await createWHO5({
				period_start: period.start,
				period_end: period.end,
				items: items as number[],
				note: note.trim() || undefined
			});
			await goto('/conditions');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save assessment.';
		} finally {
			submitting = false;
		}
	}
</script>

<Card>
	<form class="flex flex-col gap-6" onsubmit={handleSubmit}>
		{#if error}
			<p class="rounded-lg bg-red-100 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>
		{/if}

		<p class="text-sm text-gray-600 dark:text-gray-400">
			以下の5つの項目について、<strong>過去2週間</strong>のあなたの状態に最も近いものを選んでください。
		</p>

		{#each ITEMS as itemText, idx}
			<fieldset>
				<legend class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{idx + 1}. {itemText}
				</legend>
				<div class="flex flex-wrap gap-2">
					{#each [0, 1, 2, 3, 4, 5] as score}
						<button
							type="button"
							class="flex flex-col items-center gap-1 rounded-lg border-2 px-3 py-2 text-xs transition-colors
								{items[idx] === score
								? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
								: 'border-gray-200 dark:border-gray-700 hover:border-blue-300'}"
							onclick={() => (items[idx] = score)}
						>
							<span class="text-lg font-bold">{score}</span>
							<span class="text-[10px] text-gray-500 dark:text-gray-400 leading-tight text-center max-w-14">{SCALE_LABELS[score]}</span>
						</button>
					{/each}
				</div>
			</fieldset>
		{/each}

		<!-- Score display -->
		{#if rawScore !== null && percentage !== null}
			<div class="rounded-lg p-4
				{alertLevel === 'warning' ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' :
				 alertLevel === 'caution' ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800' :
				 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'}">
				<div class="flex items-baseline gap-3">
					<span class="text-3xl font-bold
						{alertLevel === 'warning' ? 'text-red-600' :
						 alertLevel === 'caution' ? 'text-yellow-600' :
						 'text-green-600'}">
						{percentage}%
					</span>
					<span class="text-sm text-gray-600 dark:text-gray-400">
						(Raw: {rawScore}/25)
					</span>
				</div>
				{#if alertLevel === 'warning'}
					<p class="mt-2 text-sm text-red-700 dark:text-red-400">
						スコアが28%以下です。抑うつ状態の可能性があります。専門家への相談を検討してください。
					</p>
				{:else if alertLevel === 'caution'}
					<p class="mt-2 text-sm text-yellow-700 dark:text-yellow-400">
						スコアが50%以下です。ウェルビーイングが低下している可能性があります。
					</p>
				{/if}
			</div>
		{/if}

		<label class="flex flex-col gap-1">
			<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Note</span>
			<textarea
				class="rounded-lg border border-gray-300 p-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
				rows="2"
				maxlength="1000"
				bind:value={note}
			></textarea>
		</label>

		<button
			type="submit"
			disabled={!allAnswered || submitting}
			class="min-h-12 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
		>
			{submitting ? 'Saving...' : 'Save Assessment'}
		</button>
	</form>
</Card>
