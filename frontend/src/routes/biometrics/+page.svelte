<script lang="ts">
	import { goto } from '$app/navigation';
	import BiometricsSummary from '$lib/components/biometrics/BiometricsSummary.svelte';
	import MetricTabs from '$lib/components/biometrics/MetricTabs.svelte';

	let { data } = $props();

	function handleDateChange(e: Event) {
		const target = e.target as HTMLInputElement;
		if (target.value) {
			goto(`/biometrics?date=${target.value}`);
		}
	}
</script>

<svelte:head>
	<title>Biometrics — VitaMetron</title>
</svelte:head>

<div class="flex items-center justify-between mb-6">
	<h1 class="text-2xl font-bold">Biometrics</h1>
	<input
		type="date"
		value={data.selectedDate}
		onchange={handleDateChange}
		class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
	/>
</div>

<BiometricsSummary summary={data.dailySummary} />
<MetricTabs summary={data.dailySummary} />
