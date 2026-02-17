<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { AnomalyDetection } from '$lib/types/biometrics';
	import { humanizeFeature } from '$lib/utils/humanize';

	let { anomaly }: { anomaly: AnomalyDetection | null } = $props();

	let isAnomaly = $derived(anomaly?.IsAnomaly ?? false);
	let topDrivers = $derived(anomaly?.TopDrivers?.slice(0, 3) ?? []);
</script>

{#if isAnomaly && anomaly}
	<Card>
		<div class="rounded-lg border-2 border-amber-400 dark:border-amber-600 p-3 -m-1">
			<div class="flex items-start gap-2">
				<span class="text-lg" aria-hidden="true">{'\u26A0\uFE0F'}</span>
				<div class="flex-1">
					<div class="flex items-center gap-1.5">
						<h3 class="text-sm font-semibold text-amber-700 dark:text-amber-400">Anomaly Detected</h3>
						<HelpTooltip text="通常パターンから外れた異常値を検出しました。スコアが高いほど通常との乖離が大きいことを示します。ドライバーは異常の主要な要因です。" />
					</div>
					{#if anomaly.Explanation}
						<p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{anomaly.Explanation}</p>
					{/if}
					{#if topDrivers.length > 0}
						<div class="mt-2 space-y-1">
							{#each topDrivers as driver}
								<div class="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
									<span class="{driver.Direction === 'positive' ? 'text-teal-500' : 'text-orange-500'}">
										{driver.Direction === 'positive' ? '\u25B2' : '\u25BC'}
									</span>
									<span>{humanizeFeature(driver.Feature)}</span>
									{#if driver.Description}
										<span class="text-gray-400">- {driver.Description}</span>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
					<p class="mt-2 text-xs text-gray-400">
						Score: {anomaly.QualityAdjustedScore.toFixed(2)} | {anomaly.ModelVersion}
					</p>
				</div>
			</div>
		</div>
	</Card>
{/if}
