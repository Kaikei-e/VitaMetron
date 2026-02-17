<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import type { VRIScore } from '$lib/types/biometrics';

	let { vri }: { vri: VRIScore | null } = $props();

	let showInfo = $state(false);

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

	let topFactors = $derived(() => {
		if (!vri?.MetricsIncluded) return [];
		return vri.MetricsIncluded.slice(0, 3);
	});
</script>

<Card>
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">VRI Score</h3>
		<button
			onclick={() => (showInfo = !showInfo)}
			class="text-gray-400 hover:text-gray-300 transition-colors"
			aria-label="VRI Score について"
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
				<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.94 6.94a.75.75 0 11-1.061-1.061 3.25 3.25 0 114.596 4.596l-.152.138-.403.364a1.75 1.75 0 00-.603 1.073.75.75 0 01-1.49-.175 3.25 3.25 0 011.12-1.992l.403-.364.044-.04a1.75 1.75 0 00-2.454-2.54zM10 15a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
			</svg>
		</button>
	</div>

	{#if showInfo}
		<div class="mt-2 p-3 rounded-md bg-gray-800/50 text-xs text-gray-300 leading-relaxed space-y-1.5">
			<p><strong class="text-gray-200">VRI (Vitality Recovery Index)</strong> は、HRV・安静時心拍・睡眠時間・睡眠規則性(SRI)・SpO2・深い睡眠・呼吸数の7指標を過去60日間のベースラインと比較し、0〜100のスコアに統合した回復度指標です。</p>
			<div class="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
				<span class="text-red-400">0–29 Low</span><span class="text-gray-400">ベースラインより大幅に低下</span>
				<span class="text-yellow-400">30–59 Moderate</span><span class="text-gray-400">ベースライン付近</span>
				<span class="text-green-400">60–79 Good</span><span class="text-gray-400">ベースラインより良好</span>
				<span class="text-green-500">80–100 Excellent</span><span class="text-gray-400">最高水準のコンディション</span>
			</div>
			<p><strong class="text-gray-200">Confidence</strong> はメトリクスの充足率・ベースライン成熟度・データ品質から算出。70%以上で信頼性が高いと判断できます。</p>
		</div>
	{/if}
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
					{vri.VRIConfidence >= 0.7 ? 'bg-green-800 text-green-200' :
					 vri.VRIConfidence >= 0.4 ? 'bg-yellow-800 text-yellow-200' :
					 'bg-red-800 text-red-200'}">
					Confidence: {(vri.VRIConfidence * 100).toFixed(0)}%
				</span>
				{#if vri.MetricsIncluded?.length}
					<p class="text-xs text-gray-400 mt-1 truncate">
						{vri.MetricsIncluded.slice(0, 3).join(', ')}
					</p>
				{/if}
			</div>
		</div>
		{#if vri.SRIValue != null}
			<p class="text-xs text-gray-400 mt-2">SRI: {vri.SRIValue.toFixed(0)}/100</p>
		{/if}
	{:else}
		<p class="mt-2 text-3xl font-bold text-gray-300 dark:text-gray-600">--</p>
		<p class="mt-1 text-xs text-gray-400">No VRI data</p>
	{/if}
</Card>
