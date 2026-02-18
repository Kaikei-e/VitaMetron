<script lang="ts">
	import WHO5Form from '$lib/components/condition/WHO5Form.svelte';
</script>

<svelte:head>
	<title>WHO-5 Assessment — VitaMetron</title>
</svelte:head>

<div class="mx-auto max-w-2xl">
	<h1 class="text-2xl font-bold mb-2">WHO-5 Well-Being Index</h1>
	<p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
		5-item self-report measure of current mental well-being (past 2 weeks)
	</p>
	<WHO5Form />
</div>
