<script lang="ts">
	import { apiFetch } from '$lib/api';
	import ConditionForm from '$lib/components/condition/ConditionForm.svelte';
	import type { TagCount } from '$lib/types/condition';

	let availableTags = $state<string[]>([]);

	$effect(() => {
		apiFetch('/api/conditions/tags')
			.then((res) => res.json())
			.then((data: TagCount[]) => {
				availableTags = data.map((t) => t.tag);
			})
			.catch(() => {});
	});
</script>

<svelte:head>
	<title>New Condition — VitaMetron</title>
</svelte:head>

<div class="mx-auto max-w-2xl">
	<h1 class="text-2xl font-bold mb-6">Record Condition</h1>
	<ConditionForm {availableTags} />
</div>
