<script lang="ts">
	let {
		metrics = []
	}: {
		metrics?: { label: string; value: string | number; unit?: string }[];
	} = $props();
</script>

<div class="grid grid-cols-2 gap-3 lg:grid-cols-3">
	{#each metrics as m}
		<div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
			<p class="text-xs text-gray-500">{m.label}</p>
			<p class="mt-1 text-lg font-semibold">
				{m.value}
				{#if m.unit}
					<span class="text-xs font-normal text-gray-400">{m.unit}</span>
				{/if}
			</p>
		</div>
	{/each}
</div>
