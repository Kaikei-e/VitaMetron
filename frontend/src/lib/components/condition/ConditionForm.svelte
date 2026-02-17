<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetch } from '$lib/api';
	import ScaleSelector from './ScaleSelector.svelte';
	import VASSlider from './VASSlider.svelte';
	import TagInput from './TagInput.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import type { CreateConditionRequest } from '$lib/types/condition';

	let { availableTags = [] }: { availableTags?: string[] } = $props();

	let overall = $state<number | null>(null);
	let mental = $state<number | null>(null);
	let physical = $state<number | null>(null);
	let energy = $state<number | null>(null);
	let overallVas = $state<number | null>(null);
	let note = $state('');
	let tags = $state<string[]>([]);
	let submitting = $state(false);
	let error = $state('');

	let isValid = $derived(overall !== null && overall >= 1 && overall <= 5);
	let noteLength = $derived(note.length);
	const NOTE_MAX = 1000;

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!isValid || submitting) return;

		error = '';
		submitting = true;

		const body: CreateConditionRequest = {
			overall: overall!
		};
		if (mental !== null) body.mental = mental;
		if (physical !== null) body.physical = physical;
		if (energy !== null) body.energy = energy;
		if (overallVas !== null) body.overall_vas = overallVas;
		if (note.trim()) body.note = note.trim();
		if (tags.length > 0) body.tags = tags;

		try {
			await apiFetch('/api/conditions', {
				method: 'POST',
				body: JSON.stringify(body)
			});
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

		<ScaleSelector label="Overall *" name="overall" bind:value={overall} />
		<ScaleSelector label="Mental" name="mental" bind:value={mental} />
		<ScaleSelector label="Physical" name="physical" bind:value={physical} />
		<ScaleSelector label="Energy" name="energy" bind:value={energy} />

		<VASSlider label="How do you feel right now? (0-100)" bind:value={overallVas} />

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
