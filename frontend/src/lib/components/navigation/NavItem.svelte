<script lang="ts">
	import { page } from '$app/state';
	import type { Snippet } from 'svelte';

	let { href, label, icon }: { href: string; label: string; icon?: Snippet } = $props();

	let isActive = $derived(
		href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(href)
	);
</script>

<a
	{href}
	class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-gray-100 dark:hover:bg-gray-800 {isActive ? 'bg-gray-100 text-blue-600 dark:bg-gray-800 dark:text-blue-400' : ''}"
	aria-current={isActive ? 'page' : undefined}
>
	{#if icon}
		{@render icon()}
	{/if}
	<span>{label}</span>
</a>
