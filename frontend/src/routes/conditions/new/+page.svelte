<script lang="ts">
	import { fetchTags } from '$lib/api/conditions';
	import ConditionForm from '$lib/components/condition/ConditionForm.svelte';

	let availableTags = $state<string[]>([]);

	$effect(() => {
		fetchTags()
			.then((tags) => (availableTags = tags))
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
