<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';

	let { label, value, unit }: { label: string; value: string | number; unit: string } = $props();
</script>

<Card>
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</h3>
	<p class="mt-2 text-2xl font-bold">
		{value}
		{#if unit}
			<span class="ml-1 text-sm font-normal text-gray-400">{unit}</span>
		{/if}
	</p>
</Card>
