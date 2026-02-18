<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import Sidebar from '$lib/components/navigation/Sidebar.svelte';
	import BottomNav from '$lib/components/navigation/BottomNav.svelte';
	import ConditionFAB from '$lib/components/condition/ConditionFAB.svelte';

	let { children } = $props();
</script>

<a
	href="#main-content"
	class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-white"
>
	Skip to main content
</a>

<div class="min-h-screen bg-gray-50 dark:bg-gray-950 dark:text-gray-100">
	<div class="hidden lg:block">
		<Sidebar />
	</div>
	<main id="main-content" class="p-4 pb-(--spacing-bottomnav) lg:ml-(--spacing-sidebar) lg:p-6 lg:pb-6">
		{@render children()}
	</main>
	<div class="lg:hidden">
		{#if page.url.pathname.startsWith('/conditions')}
			<ConditionFAB />
		{/if}
		<BottomNav />
	</div>
</div>
