<script lang="ts">
	let { text }: { text: string } = $props();
</script>

<span class="group relative inline-flex items-center">
	<button
		type="button"
		class="flex h-4 w-4 items-center justify-center rounded-full bg-gray-200 text-[10px] font-bold text-gray-500 hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-400 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600"
		aria-label="Help"
	>
		?
	</button>
	<div
		class="invisible absolute bottom-full left-1/2 z-10 mb-1.5 w-64 -translate-x-1/2 rounded-md bg-gray-800 p-2 text-xs leading-relaxed text-gray-200 shadow-lg group-hover:visible group-focus-within:visible dark:bg-gray-900 dark:text-gray-300"
		role="tooltip"
	>
		{text}
		<div class="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-gray-800 dark:border-t-gray-900"></div>
	</div>
</span>
