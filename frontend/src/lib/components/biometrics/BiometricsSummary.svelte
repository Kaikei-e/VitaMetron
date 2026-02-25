<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import type { DailySummary } from '$lib/types/biometrics';

	let { summary }: { summary: DailySummary | null } = $props();

	function formatSleep(minutes: number): string {
		const h = Math.floor(minutes / 60);
		const m = minutes % 60;
		return `${h}h ${m}m`;
	}
</script>

{#if summary}
	<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
		<Card>
			<h3 class="text-sm font-medium text-gray-500">Resting HR</h3>
			<p class="mt-1 text-2xl font-bold">{summary.RestingHR}<span class="ml-1 text-sm font-normal text-gray-400">bpm</span></p>
		</Card>
		<Card>
			<h3 class="text-sm font-medium text-gray-500">HRV</h3>
			<p class="mt-1 text-2xl font-bold">{summary.HRVDailyRMSSD?.toFixed(1) ?? '--'}<span class="ml-1 text-sm font-normal text-gray-400">ms</span></p>
		</Card>
		<Card>
			<h3 class="text-sm font-medium text-gray-500">Sleep</h3>
			<p class="mt-1 text-2xl font-bold">{formatSleep(summary.SleepDurationMin)}</p>
		</Card>
		<Card>
			<h3 class="text-sm font-medium text-gray-500">Steps</h3>
			<p class="mt-1 text-2xl font-bold">{summary.Steps.toLocaleString()}</p>
		</Card>
	</div>
{:else}
	<Card>
		<h3 class="text-sm font-medium text-gray-500 mb-2">Biometrics Summary</h3>
		<p class="text-gray-400">No biometric data available for this date.</p>
	</Card>
{/if}
