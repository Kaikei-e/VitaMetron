<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import { humanizeVRIMetric } from '$lib/utils/humanize';
	import type { VRIScore } from '$lib/types/biometrics';

	let { vri }: { vri: VRIScore | null } = $props();

	function scoreColor(score: number): string {
		if (score < 30) return '#ef4444';
		if (score < 60) return '#eab308';
		if (score < 80) return '#22c55e';
		return '#16a34a';
	}

	function scoreLabel(score: number): string {
		if (score < 30) return 'Low';
		if (score < 60) return 'Moderate';
		if (score < 80) return 'Good';
		return 'Excellent';
	}

	let color = $derived(vri ? scoreColor(vri.VRIScore) : '#6b7280');
	let label = $derived(vri ? scoreLabel(vri.VRIScore) : '--');
	let dashArray = $derived(vri ? `${(vri.VRIScore / 100) * 251.2} 251.2` : '0 251.2');

	let maxContribution = $derived(() => {
		if (!vri?.ContributingFactors?.length) return 0;
		return Math.max(...vri.ContributingFactors.map((f) => Math.abs(f.contribution)));
	});
</script>

<Card>
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-1.5">
			<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">VRI Score</h3>
			<HelpTooltip text="VRI (Vitality Recovery Index): HRV・心拍・睡眠など7指標を過去60日のベースラインと比較した回復度スコア (0-100)。Confidence 70%以上で信頼性が高いと判断できます。" />
		</div>
	</div>

	{#if vri}
		<div class="flex items-center gap-4 mt-2">
			<!-- Circular gauge -->
			<div class="relative w-20 h-20 flex-shrink-0">
				<svg viewBox="0 0 100 100" class="w-full h-full -rotate-90">
					<circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" stroke-width="8"
						class="text-gray-200 dark:text-gray-700" />
					<circle cx="50" cy="50" r="40" fill="none" stroke={color} stroke-width="8"
						stroke-linecap="round" stroke-dasharray={dashArray} />
				</svg>
				<span class="absolute inset-0 flex items-center justify-center text-lg font-bold" style:color>
					{Math.round(vri.VRIScore)}
				</span>
			</div>
			<div class="flex-1 min-w-0">
				<p class="text-lg font-semibold" style:color>{label}</p>
				<!-- Confidence badge -->
				<span class="text-xs px-2 py-0.5 rounded-full font-medium
					{vri.VRIConfidence >= 0.7 ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200' :
					 vri.VRIConfidence >= 0.4 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-800 dark:text-yellow-200' :
					 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-200'}">
					Confidence: {(vri.VRIConfidence * 100).toFixed(0)}%
				</span>
				{#if vri.MetricsIncluded?.length}
					<p class="text-xs text-gray-400 mt-1 truncate">
						{vri.MetricsIncluded.slice(0, 3).join(', ')}
					</p>
				{/if}
			</div>
		</div>

		<!-- Contributing factors breakdown -->
		{#if vri.ContributingFactors?.length}
			<div class="mt-3 space-y-1">
				{#each vri.ContributingFactors as factor}
					{@const max = maxContribution()}
					{@const pct = max > 0 ? (Math.abs(factor.contribution) / max) * 100 : 0}
					<div class="flex items-center gap-2 text-xs">
						<span class="w-16 text-gray-400 truncate flex-shrink-0">{humanizeVRIMetric(factor.metric)}</span>
						<div class="flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
							<div
								class="h-full rounded-full {factor.direction === 'positive' ? 'bg-green-500' : 'bg-red-500'}"
								style:width="{pct}%"
							></div>
						</div>
						{#if factor.direction === 'positive'}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3 text-green-500 flex-shrink-0">
								<path fill-rule="evenodd" d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" clip-rule="evenodd" />
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3 text-red-500 flex-shrink-0">
								<path fill-rule="evenodd" d="M8 2a.75.75 0 0 1 .75.75v8.69l3.22-3.22a.75.75 0 1 1 1.06 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.22 3.22V2.75A.75.75 0 0 1 8 2Z" clip-rule="evenodd" />
							</svg>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		{#if vri.SRIValue != null}
			<p class="text-xs text-gray-400 mt-2">SRI: {vri.SRIValue.toFixed(0)}/100</p>
		{/if}
	{:else}
		<p class="mt-2 text-3xl font-bold text-gray-300 dark:text-gray-600">--</p>
		<p class="mt-1 text-xs text-gray-400">No VRI data</p>
	{/if}
</Card>
