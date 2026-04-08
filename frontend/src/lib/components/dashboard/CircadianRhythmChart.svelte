<script lang="ts">
	import Card from '$lib/components/ui/Card.svelte';
	import HelpTooltip from '$lib/components/ui/HelpTooltip.svelte';
	import type { CircadianScore, HeartRateSample } from '$lib/types/biometrics';

	let {
		circadian,
		hrSamples
	}: { circadian: CircadianScore | null; hrSamples: HeartRateSample[] } = $props();

	const SIZE = 280;
	const CX = SIZE / 2;
	const CY = SIZE / 2;
	const R_OUTER = 120;
	const R_INNER = 40;
	const HOURS = 24;

	// Bin HR samples into hourly averages
	let hourlyHR = $derived(() => {
		if (!hrSamples.length) return new Array(24).fill(null);
		const bins: number[][] = Array.from({ length: 24 }, () => []);
		for (const s of hrSamples) {
			const h = new Date(s.Time).getHours();
			bins[h].push(s.BPM);
		}
		return bins.map((b) => (b.length > 0 ? b.reduce((a, c) => a + c, 0) / b.length : null));
	});

	// Compute cosinor fit curve points
	let cosinorCurve = $derived(() => {
		if (!circadian?.CosinorMesor || !circadian?.CosinorAmplitude || circadian?.CosinorAcrophaseHour == null)
			return null;
		const points: number[] = [];
		const M = circadian.CosinorMesor;
		const A = circadian.CosinorAmplitude;
		const phi = (circadian.CosinorAcrophaseHour * Math.PI * 2) / 24;
		for (let h = 0; h < 24; h++) {
			const t = (h * Math.PI * 2) / 24;
			points.push(M + A * Math.cos(t - phi));
		}
		return points;
	});

	// Get HR range for scaling
	let hrRange = $derived(() => {
		const values = hourlyHR().filter((v): v is number => v != null);
		const cosinor = cosinorCurve();
		if (cosinor) values.push(...cosinor);
		if (values.length === 0) return { min: 50, max: 100 };
		return { min: Math.min(...values) - 5, max: Math.max(...values) + 5 };
	});

	function polarPoint(hour: number, value: number): { x: number; y: number } {
		const range = hrRange();
		const normalizedR = ((value - range.min) / (range.max - range.min)) * (R_OUTER - R_INNER) + R_INNER;
		// 0h at top, clockwise
		const angle = ((hour / HOURS) * Math.PI * 2 - Math.PI / 2);
		return {
			x: CX + normalizedR * Math.cos(angle),
			y: CY + normalizedR * Math.sin(angle)
		};
	}

	function pathFromValues(values: (number | null)[]): string {
		const parts: string[] = [];
		let started = false;
		for (let h = 0; h < 24; h++) {
			const v = values[h];
			if (v == null) {
				started = false;
				continue;
			}
			const { x, y } = polarPoint(h, v);
			parts.push(started ? `L${x.toFixed(1)},${y.toFixed(1)}` : `M${x.toFixed(1)},${y.toFixed(1)}`);
			started = true;
		}
		// Close if full
		if (parts.length >= 23) {
			const first = values[0];
			if (first != null) {
				const { x, y } = polarPoint(0, first);
				parts.push(`L${x.toFixed(1)},${y.toFixed(1)}`);
			}
		}
		return parts.join(' ');
	}

	// M10/L5 arcs
	function arcPath(startHour: number, durationHours: number, radius: number): string {
		const startAngle = (startHour / 24) * Math.PI * 2 - Math.PI / 2;
		const endAngle = ((startHour + durationHours) / 24) * Math.PI * 2 - Math.PI / 2;
		const largeArc = durationHours > 12 ? 1 : 0;
		const x1 = CX + radius * Math.cos(startAngle);
		const y1 = CY + radius * Math.sin(startAngle);
		const x2 = CX + radius * Math.cos(endAngle);
		const y2 = CY + radius * Math.sin(endAngle);
		return `M${x1.toFixed(1)},${y1.toFixed(1)} A${radius},${radius} 0 ${largeArc},1 ${x2.toFixed(1)},${y2.toFixed(1)}`;
	}

	let hrDataPath = $derived(pathFromValues(hourlyHR()));
	let cosinorPath = $derived(() => {
		const c = cosinorCurve();
		return c ? pathFromValues(c) : '';
	});
</script>

<Card>
	<div class="flex items-center gap-1.5 mb-2">
		<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">24h Heart Rate Rhythm</h3>
		<HelpTooltip
			text="24時間の心拍リズム。実測HR平均(青)にコサイナーフィットカーブ(赤)をオーバーレイ。オレンジ=M10(最も活動的な10時間)、紫=L5(最も安静な5時間)。"
		/>
	</div>

	{#if hrSamples.length > 0}
		<div class="flex justify-center">
			<svg viewBox="0 0 {SIZE} {SIZE}" class="w-full max-w-[280px]">
				<!-- Hour labels -->
				{#each Array(24) as _, h}
					{@const angle = (h / 24) * Math.PI * 2 - Math.PI / 2}
					{@const lx = CX + (R_OUTER + 14) * Math.cos(angle)}
					{@const ly = CY + (R_OUTER + 14) * Math.sin(angle)}
					{#if h % 3 === 0}
						<text
							x={lx}
							y={ly}
							text-anchor="middle"
							dominant-baseline="central"
							class="fill-gray-400 text-[9px]">{h}</text
						>
					{/if}
					<!-- Grid lines -->
					{@const gx1 = CX + R_INNER * Math.cos(angle)}
					{@const gy1 = CY + R_INNER * Math.sin(angle)}
					{@const gx2 = CX + R_OUTER * Math.cos(angle)}
					{@const gy2 = CY + R_OUTER * Math.sin(angle)}
					<line
						x1={gx1}
						y1={gy1}
						x2={gx2}
						y2={gy2}
						class="stroke-gray-200 dark:stroke-gray-700"
						stroke-width="0.5"
					/>
				{/each}

				<!-- Concentric grid circles -->
				<circle cx={CX} cy={CY} r={R_INNER} fill="none" class="stroke-gray-200 dark:stroke-gray-700" stroke-width="0.5" />
				<circle cx={CX} cy={CY} r={(R_INNER + R_OUTER) / 2} fill="none" class="stroke-gray-200 dark:stroke-gray-700" stroke-width="0.5" stroke-dasharray="2,2" />
				<circle cx={CX} cy={CY} r={R_OUTER} fill="none" class="stroke-gray-200 dark:stroke-gray-700" stroke-width="0.5" />

				<!-- M10 arc (warm color) -->
				{#if circadian?.NPARM10Start != null}
					<path
						d={arcPath(circadian.NPARM10Start, 10, R_OUTER + 4)}
						fill="none"
						stroke="#f97316"
						stroke-width="3"
						stroke-linecap="round"
						opacity="0.6"
					/>
				{/if}

				<!-- L5 arc (cool color) -->
				{#if circadian?.NPARL5Start != null}
					<path
						d={arcPath(circadian.NPARL5Start, 5, R_OUTER + 4)}
						fill="none"
						stroke="#8b5cf6"
						stroke-width="3"
						stroke-linecap="round"
						opacity="0.6"
					/>
				{/if}

				<!-- Actual HR data -->
				<path d={hrDataPath} fill="none" stroke="#3b82f6" stroke-width="2" opacity="0.7" />

				<!-- HR data points -->
				{#each hourlyHR() as hr, h}
					{#if hr != null}
						{@const pt = polarPoint(h, hr)}
						<circle cx={pt.x} cy={pt.y} r="2.5" fill="#3b82f6" opacity="0.8" />
					{/if}
				{/each}

				<!-- Cosinor fit curve -->
				{#if cosinorPath()}
					<path d={cosinorPath()} fill="none" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4,2" opacity="0.8" />
				{/if}

				<!-- Center info -->
				{#if circadian}
					<text x={CX} y={CY - 6} text-anchor="middle" class="fill-gray-500 dark:fill-gray-400 text-[9px]">MESOR</text>
					<text x={CX} y={CY + 8} text-anchor="middle" class="fill-gray-700 dark:fill-gray-200 text-[11px] font-semibold">
						{circadian.CosinorMesor?.toFixed(0) ?? '--'}
					</text>
				{/if}
			</svg>
		</div>

		<!-- Legend -->
		<div class="flex flex-wrap justify-center gap-3 mt-2 text-xs text-gray-400">
			<span class="flex items-center gap-1">
				<span class="w-3 h-0.5 bg-blue-500 inline-block rounded"></span> HR
			</span>
			<span class="flex items-center gap-1">
				<span class="w-3 h-0.5 bg-red-500 inline-block rounded" style="border-top: 1px dashed;"></span> Cosinor
			</span>
			<span class="flex items-center gap-1">
				<span class="w-3 h-0.5 bg-orange-500 inline-block rounded"></span> M10
			</span>
			<span class="flex items-center gap-1">
				<span class="w-3 h-0.5 bg-violet-500 inline-block rounded"></span> L5
			</span>
		</div>
	{:else}
		<p class="text-center text-sm text-gray-400 py-8">No heart rate data</p>
	{/if}
</Card>
