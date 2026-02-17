<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-900 dark:shadow-none dark:border dark:border-gray-800">
	{@render children()}
</div>
