<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';

	let { signals = [] }: { signals?: string[] } = $props();

	const severityMap: Record<string, { color: string; icon: string; level: string }> = {
		elevated_rhr: { color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: '\u{1F534}', level: 'alert' },
		very_low_hrv: { color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: '\u{1F534}', level: 'alert' },
		poor_sleep: { color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400', icon: '\u{1F7E1}', level: 'advisory' },
		low_hrv: { color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400', icon: '\u{1F7E1}', level: 'advisory' },
		short_sleep: { color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400', icon: '\u{1F7E1}', level: 'advisory' },
		low_activity: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', icon: '\u{1F535}', level: 'info' },
		irregular_sleep: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', icon: '\u{1F535}', level: 'info' }
	};

	const defaultSeverity = { color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400', icon: '\u{2139}\u{FE0F}', level: 'info' };

	function getSeverity(signal: string) {
		return severityMap[signal] ?? defaultSeverity;
	}

	function formatSignal(signal: string): string {
		return signal.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}
</script>

<Card>
	<div class="flex items-center gap-1.5">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Risk Signals</h3>
		<HelpTooltip text="バイオメトリクスから検出されたリスクシグナルです。赤は要注意、黄は注意、青は参考情報を表します。" />
	</div>
	{#if signals.length > 0}
		<div class="mt-3 flex flex-wrap gap-2">
			{#each signals as signal}
				{@const sev = getSeverity(signal)}
				<span
					class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium {sev.color}"
					role="status"
				>
					<span aria-hidden="true">{sev.icon}</span>
					{formatSignal(signal)}
				</span>
			{/each}
		</div>
	{:else}
		<p class="mt-3 text-sm text-green-600 dark:text-green-400">No risk signals detected</p>
	{/if}
</Card>
