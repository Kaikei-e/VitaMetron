<script lang="ts">
	import { goto } from '$app/navigation';
	import { createCondition } from '$lib/api/conditions';
	import { todayISO } from '$lib/utils/date';
	import VASSlider from './VASSlider.svelte';
	import TagInput from './TagInput.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import type { CreateConditionRequest } from '$lib/types/condition';

	let { availableTags = [] }: { availableTags?: string[] } = $props();

	let logDate = $state(todayISO());
	let wellbeing = $state<number | null>(null);
	let mood = $state<number | null>(null);
	let energy = $state<number | null>(null);
	let sleepQuality = $state<number | null>(null);
	let stress = $state<number | null>(null);
	let note = $state('');
	let tags = $state<string[]>([]);
	let submitting = $state(false);
	let error = $state('');

	let isValid = $derived(wellbeing !== null && wellbeing >= 0 && wellbeing <= 100);
	let noteLength = $derived(note.length);
	const NOTE_MAX = 1000;

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!isValid || submitting) return;

		error = '';
		submitting = true;

		const body: CreateConditionRequest = {
			wellbeing: wellbeing!
		};
		if (mood !== null) body.mood = mood;
		if (energy !== null) body.energy = energy;
		if (sleepQuality !== null) body.sleep_quality = sleepQuality;
		if (stress !== null) body.stress = stress;
		if (note.trim()) body.note = note.trim();
		if (tags.length > 0) body.tags = tags;
		body.logged_at = `${logDate}T12:00:00Z`;

		try {
			await createCondition(body);
			await goto('/conditions');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save condition.';
		} finally {
			submitting = false;
		}
	}
</script>

<Card>
	<form class="flex flex-col gap-4" onsubmit={handleSubmit}>
		{#if error}
			<p class="rounded-lg bg-red-100 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>
		{/if}

		<label class="flex flex-col gap-1">
			<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Date</span>
			<input
				type="date"
				class="rounded-lg border border-gray-300 p-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
				max={todayISO()}
				bind:value={logDate}
			/>
		</label>

		<VASSlider
			label="Well-being"
			leftLabel="最悪の状態"
			rightLabel="最高の状態"
			required={true}
			bind:value={wellbeing}
		/>

		<VASSlider
			label="Mood"
			leftLabel="非常に落ち込んでいる"
			rightLabel="非常に気分が良い"
			bind:value={mood}
		/>

		<VASSlider
			label="Energy"
			leftLabel="完全に疲労"
			rightLabel="非常に活力がある"
			bind:value={energy}
		/>

		<VASSlider
			label="Sleep Quality"
			leftLabel="非常に悪い"
			rightLabel="非常に良い"
			bind:value={sleepQuality}
		/>

		<VASSlider
			label="Stress"
			leftLabel="極度のストレス"
			rightLabel="完全にリラックス"
			bind:value={stress}
		/>

		<label class="flex flex-col gap-1">
			<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Note</span>
			<textarea
				class="rounded-lg border border-gray-300 p-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
				rows="3"
				maxlength={NOTE_MAX}
				bind:value={note}
			></textarea>
			<span class="text-xs text-gray-400 text-right">{noteLength}/{NOTE_MAX}</span>
		</label>

		<TagInput bind:tags suggestions={availableTags} />

		<button
			type="submit"
			disabled={!isValid || submitting}
			class="min-h-12 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
		>
			{submitting ? 'Saving...' : 'Save'}
		</button>
	</form>
</Card>
