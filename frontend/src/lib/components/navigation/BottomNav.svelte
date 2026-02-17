<script lang="ts">
	import { page } from '$app/state';
	import DashboardIcon from '$lib/components/icons/DashboardIcon.svelte';
	import ConditionsIcon from '$lib/components/icons/ConditionsIcon.svelte';
	import BiometricsIcon from '$lib/components/icons/BiometricsIcon.svelte';
	import InsightsIcon from '$lib/components/icons/InsightsIcon.svelte';
	import SettingsIcon from '$lib/components/icons/SettingsIcon.svelte';

	const items = [
		{ href: '/', label: 'Dashboard', icon: DashboardIcon },
		{ href: '/conditions', label: 'Conditions', icon: ConditionsIcon },
		{ href: '/biometrics', label: 'Biometrics', icon: BiometricsIcon },
		{ href: '/insights', label: 'Insights', icon: InsightsIcon },
		{ href: '/settings', label: 'Settings', icon: SettingsIcon }
	] as const;

	function isActive(href: string): boolean {
		return href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(href);
	}
</script>

<nav
	class="fixed bottom-0 left-0 right-0 z-40 flex h-(--spacing-bottomnav) items-center justify-around border-t border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900"
	aria-label="Main navigation"
>
	{#each items as item}
		<a
			href={item.href}
			class="flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-lg px-3 py-1 text-xs font-medium transition-colors {isActive(item.href) ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}"
			aria-current={isActive(item.href) ? 'page' : undefined}
		>
			<item.icon size={20} />
			<span>{item.label}</span>
		</a>
	{/each}
</nav>
