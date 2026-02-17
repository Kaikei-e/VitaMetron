<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		tabs,
		panel0,
		panel1,
		panel2
	}: {
		tabs: string[];
		panel0: Snippet;
		panel1: Snippet;
		panel2: Snippet;
	} = $props();

	let activeIndex = $state(0);

	let panels = $derived([panel0, panel1, panel2]);

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			activeIndex = (activeIndex + 1) % tabs.length;
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			activeIndex = (activeIndex - 1 + tabs.length) % tabs.length;
		}
	}
</script>

<div>
	<div
		class="flex border-b border-gray-200 dark:border-gray-700 mb-4"
		role="tablist"
		aria-label="Dashboard views"
	>
		{#each tabs as tab, i}
			<button
				role="tab"
				aria-selected={activeIndex === i}
				id="dtab-{i}"
				aria-controls="dpanel-{i}"
				tabindex={activeIndex === i ? 0 : -1}
				class="min-h-12 flex-1 px-3 py-2 text-sm font-medium transition-colors"
				class:border-b-2={activeIndex === i}
				class:border-blue-600={activeIndex === i}
				class:text-blue-600={activeIndex === i}
				class:dark:border-blue-400={activeIndex === i}
				class:dark:text-blue-400={activeIndex === i}
				class:text-gray-500={activeIndex !== i}
				class:dark:text-gray-400={activeIndex !== i}
				onclick={() => (activeIndex = i)}
				onkeydown={handleKeydown}
			>
				{tab}
			</button>
		{/each}
	</div>

	{#each panels as panel, i}
		{#if activeIndex === i}
			<div role="tabpanel" id="dpanel-{i}" aria-labelledby="dtab-{i}">
				{@render panel()}
			</div>
		{/if}
	{/each}
</div>
