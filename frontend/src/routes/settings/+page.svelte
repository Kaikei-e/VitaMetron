<script lang="ts">
	import FitbitSection from '$lib/components/settings/FitbitSection.svelte';
	import HealthConnectImport from '$lib/components/settings/HealthConnectImport.svelte';
	import HealthKitImport from '$lib/components/settings/HealthKitImport.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>Settings — VitaMetron</title>
</svelte:head>

<h1 class="text-2xl font-bold mb-6">Settings</h1>

<FitbitSection connected={data.fitbitConnected} fitbitResult={data.fitbitResult} />
<HealthConnectImport />
<HealthKitImport />
