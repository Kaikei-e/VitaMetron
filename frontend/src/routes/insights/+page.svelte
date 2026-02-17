<script lang="ts">
	import InsightsTabs from '$lib/components/insights/InsightsTabs.svelte';
	import ForecastHero from '$lib/components/insights/ForecastHero.svelte';
	import HRVPredictionCard from '$lib/components/insights/HRVPredictionCard.svelte';
	import ContributingFactors from '$lib/components/insights/ContributingFactors.svelte';
	import RiskSignals from '$lib/components/insights/RiskSignals.svelte';
	import AnomalyAlert from '$lib/components/insights/AnomalyAlert.svelte';
	import WeeklySummary from '$lib/components/insights/WeeklySummary.svelte';
	import AnomalyHeatstrip from '$lib/components/insights/AnomalyHeatstrip.svelte';
	import ModelStatusCard from '$lib/components/insights/ModelStatusCard.svelte';
	import SkeletonCard from '$lib/components/ui/SkeletonCard.svelte';

	let { data } = $props();
</script>

<svelte:head>
	<title>Insights - VitaMetron</title>
</svelte:head>

<div class="mx-auto max-w-3xl space-y-4">
	<h1 class="text-2xl font-bold">Predictions & Insights</h1>

	<InsightsTabs tabs={["Tomorrow's Forecast", 'Weekly Review']}>
		{#snippet panel0()}
			<div class="space-y-4">
				{#await data.insights}
					<SkeletonCard />
				{:then insights}
					<ForecastHero prediction={insights?.Prediction ?? null} />
					<ContributingFactors factors={insights?.Prediction?.ContributingFactors} />
					<RiskSignals signals={insights?.Risks} />
				{/await}

				<div class="grid gap-4 sm:grid-cols-2">
					{#await data.hrvPrediction}
						<SkeletonCard />
					{:then hrvPrediction}
						<HRVPredictionCard prediction={hrvPrediction} />
					{/await}
					<AnomalyAlert anomaly={data.anomaly} />
				</div>
			</div>
		{/snippet}

		{#snippet panel1()}
			<div class="space-y-4">
				{#await data.weeklyInsight}
					<SkeletonCard />
				{:then weeklyInsight}
					<WeeklySummary insight={weeklyInsight} />
				{/await}

				<AnomalyHeatstrip anomalies={data.anomalyRange} />

				{#await data.hrvStatus}
					<SkeletonCard />
				{:then hrvStatus}
					<ModelStatusCard status={hrvStatus} />
				{/await}
			</div>
		{/snippet}
	</InsightsTabs>
</div>
