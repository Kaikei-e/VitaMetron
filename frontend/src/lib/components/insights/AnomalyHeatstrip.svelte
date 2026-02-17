<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { AnomalyDetection } from '$lib/types/biometrics';

	let { anomalies = [] }: { anomalies?: AnomalyDetection[] } = $props();

	const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

	function getColor(a: AnomalyDetection | undefined): string {
		if (!a) return 'bg-gray-200 dark:bg-gray-700';
		const score = a.QualityAdjustedScore;
		if (a.IsAnomaly) return 'bg-orange-400 dark:bg-orange-500';
		if (score > 0.5) return 'bg-yellow-300 dark:bg-yellow-500';
		return 'bg-green-400 dark:bg-green-500';
	}

	function getAriaLabel(a: AnomalyDetection | undefined, day: string): string {
		if (!a) return `${day}: no data`;
		if (a.IsAnomaly) return `${day}: anomaly detected (score ${a.QualityAdjustedScore.toFixed(2)})`;
		return `${day}: normal (score ${a.QualityAdjustedScore.toFixed(2)})`;
	}

	let sortedAnomalies = $derived.by(() => {
		const sorted = [...anomalies].sort(
			(a, b) => new Date(a.Date).getTime() - new Date(b.Date).getTime()
		);
		// Pad to 7 days
		while (sorted.length < 7) {
			sorted.push(undefined as unknown as AnomalyDetection);
		}
		return sorted.slice(0, 7);
	});
</script>

<Card>
	<div class="flex items-center gap-1.5">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">7-Day Anomaly Pattern</h3>
		<HelpTooltip text="過去7日間の異常検出パターンです。緑は正常、黄はやや高め、オレンジは異常検出を示します。灰色はデータなしです。" />
	</div>
	<div class="mt-3 flex gap-1.5" role="img" aria-label="7-day anomaly heatstrip">
		{#each sortedAnomalies as a, i}
			<div class="flex flex-1 flex-col items-center gap-1">
				<span class="text-xs text-gray-500 dark:text-gray-400">{dayLabels[i]}</span>
				<div
					class="h-6 w-full rounded {getColor(a)}"
					title={getAriaLabel(a, dayLabels[i])}
					role="presentation"
				></div>
			</div>
		{/each}
	</div>
	<div class="mt-2 flex items-center gap-4 text-xs text-gray-400">
		<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-full bg-green-400"></span> Normal</span>
		<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-full bg-yellow-300"></span> Elevated</span>
		<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-full bg-orange-400"></span> Anomaly</span>
	</div>
</Card>
