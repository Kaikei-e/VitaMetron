<script lang="ts">
	import { vasToLabel } from '$lib/utils/condition';

	let {
		label = 'How do you feel right now? (0-100)',
		leftLabel = '',
		rightLabel = '',
		required = false,
		value = $bindable<number | null>(null)
	}: {
		label?: string;
		leftLabel?: string;
		rightLabel?: string;
		required?: boolean;
		value?: number | null;
	} = $props();

	let active = $state(false);

	// Auto-activate for required fields
	$effect(() => {
		if (required && !active && value === null) {
			active = true;
			value = 50;
		}
	});

	function activate() {
		if (!active) {
			active = true;
			value = 50;
		}
	}

	function clear() {
		if (required) return;
		active = false;
		value = null;
	}

	let color = $derived.by(() => {
		if (value === null) return 'bg-gray-300 dark:bg-gray-600';
		if (value < 25) return 'text-red-600';
		if (value < 50) return 'text-orange-500';
		if (value < 75) return 'text-yellow-500';
		return 'text-green-600';
	});

	let displayLabel = $derived(vasToLabel(value));

	let anchorLeft = $derived(leftLabel || 'Very Poor');
	let anchorRight = $derived(rightLabel || 'Excellent');
</script>

<fieldset>
	<legend class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
		{label}{#if required}<span class="text-red-500 ml-0.5">*</span>{/if}
	</legend>

	{#if !active}
		<button
			type="button"
			class="w-full rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors"
			onclick={activate}
		>
			Tap to rate on a 0-100 scale{#if !required} (optional){/if}
		</button>
	{:else}
		<div class="flex flex-col gap-2">
			<div class="flex items-center justify-between">
				<span class="text-2xl font-bold {color}">{value}</span>
				<span class="text-sm text-gray-500 dark:text-gray-400">{displayLabel}</span>
				{#if !required}
					<button
						type="button"
						class="text-xs text-gray-400 hover:text-red-500 transition-colors"
						onclick={clear}
					>
						Clear
					</button>
				{/if}
			</div>

			<input
				type="range"
				min="0"
				max="100"
				step="1"
				bind:value={value}
				aria-label="{label}"
				class="w-full h-2 rounded-lg appearance-none cursor-pointer accent-blue-600"
				style="background: linear-gradient(to right, #ef4444 0%, #f59e0b 50%, #22c55e 100%);"
			/>

			<div class="flex justify-between text-xs text-gray-400 dark:text-gray-500">
				<span>{anchorLeft}</span>
				<span>{anchorRight}</span>
			</div>
		</div>
	{/if}
</fieldset>
