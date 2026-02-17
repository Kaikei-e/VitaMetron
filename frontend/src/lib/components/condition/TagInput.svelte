<script lang="ts">
	let {
		tags = $bindable<string[]>([]),
		suggestions = []
	}: {
		tags?: string[];
		suggestions?: string[];
	} = $props();

	let input = $state('');
	let showSuggestions = $state(false);

	let filteredSuggestions = $derived(
		input.trim()
			? suggestions.filter(
					(s) => s.toLowerCase().includes(input.toLowerCase()) && !tags.includes(s)
				)
			: []
	);

	function addTag(tag?: string) {
		const t = (tag ?? input).trim();
		if (t && !tags.includes(t)) {
			tags = [...tags, t];
			input = '';
			showSuggestions = false;
		}
	}

	function removeTag(tag: string) {
		tags = tags.filter((t) => t !== tag);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addTag();
		} else if (e.key === 'Escape') {
			showSuggestions = false;
		}
	}
</script>

<div class="relative">
	<label for="tag-input" class="text-sm font-medium text-gray-700 dark:text-gray-300">Tags</label>
	<div class="mt-1 flex flex-wrap gap-1">
		{#each tags as tag}
			<span class="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-xs dark:bg-gray-800">
				{tag}
				<button
					type="button"
					class="min-h-5 min-w-5 text-gray-400 hover:text-gray-600"
					onclick={() => removeTag(tag)}
					aria-label="Remove tag {tag}"
				>
					&times;
				</button>
			</span>
		{/each}
	</div>
	<input
		id="tag-input"
		type="text"
		class="mt-1 w-full rounded-lg border border-gray-300 p-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
		placeholder="Add tag..."
		autocomplete="off"
		bind:value={input}
		onfocus={() => (showSuggestions = true)}
		onblur={() => setTimeout(() => (showSuggestions = false), 150)}
		onkeydown={handleKeydown}
	/>
	{#if showSuggestions && filteredSuggestions.length > 0}
		<ul class="absolute z-10 mt-1 max-h-40 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
			{#each filteredSuggestions as suggestion}
				<li>
					<button
						type="button"
						class="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
						onmousedown={(e: MouseEvent) => { e.preventDefault(); addTag(suggestion); }}
					>
						{suggestion}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>
