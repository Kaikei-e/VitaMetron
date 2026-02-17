<script lang="ts">
	let { label, name, value = $bindable<number | null>(null) }: { label: string; name: string; value?: number | null } = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
			e.preventDefault();
			value = Math.min((value ?? 0) + 1, 5);
		} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
			e.preventDefault();
			value = Math.max((value ?? 2) - 1, 1);
		}
	}
</script>

<fieldset role="radiogroup" aria-label="{label} score">
	<legend class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</legend>
	<div class="flex gap-2">
		{#each [1, 2, 3, 4, 5] as score}
			<button
				type="button"
				role="radio"
				aria-checked={value === score}
				tabindex={value === score || (value === null && score === 1) ? 0 : -1}
				class="h-12 w-12 rounded-full border-2 text-sm font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 {value !== score ? 'border-gray-300 dark:border-gray-600' : 'border-transparent'}"
				class:text-white={value === score}
				onclick={() => (value = score)}
				onkeydown={handleKeydown}
			>
				<span
					class="flex h-full w-full items-center justify-center rounded-full"
					class:bg-condition-1={value === score && score === 1}
					class:bg-condition-2={value === score && score === 2}
					class:bg-condition-3={value === score && score === 3}
					class:bg-condition-4={value === score && score === 4}
					class:bg-condition-5={value === score && score === 5}
				>
					{score}
				</span>
			</button>
		{/each}
	</div>
	<input type="hidden" {name} value={value ?? ''} />
</fieldset>
