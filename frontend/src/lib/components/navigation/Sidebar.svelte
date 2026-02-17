<script lang="ts">
	import NavItem from './NavItem.svelte';
	import DashboardIcon from '$lib/components/icons/DashboardIcon.svelte';
	import ConditionsIcon from '$lib/components/icons/ConditionsIcon.svelte';
	import BiometricsIcon from '$lib/components/icons/BiometricsIcon.svelte';
	import InsightsIcon from '$lib/components/icons/InsightsIcon.svelte';
	import SettingsIcon from '$lib/components/icons/SettingsIcon.svelte';
</script>

<aside class="fixed top-0 left-0 h-full w-(--spacing-sidebar) border-r border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900" aria-label="Main navigation">
	<h2 class="mb-6 text-xl font-bold">VitaMetron</h2>
	<nav class="flex flex-col gap-1">
		<NavItem href="/" label="Dashboard">
			{#snippet icon()}<DashboardIcon size={20} />{/snippet}
		</NavItem>
		<NavItem href="/conditions" label="Conditions">
			{#snippet icon()}<ConditionsIcon size={20} />{/snippet}
		</NavItem>
		<NavItem href="/biometrics" label="Biometrics">
			{#snippet icon()}<BiometricsIcon size={20} />{/snippet}
		</NavItem>
		<NavItem href="/insights" label="Insights">
			{#snippet icon()}<InsightsIcon size={20} />{/snippet}
		</NavItem>
		<NavItem href="/settings" label="Settings">
			{#snippet icon()}<SettingsIcon size={20} />{/snippet}
		</NavItem>
	</nav>
</aside>
