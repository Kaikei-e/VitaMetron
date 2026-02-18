/** Legacy 1-5 scale colors (kept for backward compat) */
export const SCORE_TEXT_COLOR: Record<number, string> = {
	1: 'text-condition-1',
	2: 'text-condition-2',
	3: 'text-condition-3',
	4: 'text-condition-4',
	5: 'text-condition-5'
};

export const SCORE_BG_COLOR: Record<number, string> = {
	1: 'bg-condition-1',
	2: 'bg-condition-2',
	3: 'bg-condition-3',
	4: 'bg-condition-4',
	5: 'bg-condition-5'
};

export const SCORE_LABEL: Record<number, string> = {
	1: 'Critical',
	2: 'Low',
	3: 'Neutral',
	4: 'Good',
	5: 'Excellent'
};

/** VAS 0-100 label */
export function vasToLabel(score: number | null): string {
	if (score === null) return '';
	if (score <= 10) return 'Very Poor';
	if (score <= 30) return 'Poor';
	if (score <= 50) return 'Fair';
	if (score <= 70) return 'Good';
	if (score <= 90) return 'Very Good';
	return 'Excellent';
}

/** VAS 0-100 → Tailwind text color class */
export function vasToTextColor(score: number | null): string {
	if (score === null) return 'text-gray-400';
	if (score < 25) return 'text-red-600';
	if (score < 50) return 'text-orange-500';
	if (score < 75) return 'text-yellow-500';
	return 'text-green-600';
}

/** VAS 0-100 → Tailwind bg color class */
export function vasToBgColor(score: number | null): string {
	if (score === null) return 'bg-gray-400';
	if (score < 25) return 'bg-red-500';
	if (score < 50) return 'bg-orange-500';
	if (score < 75) return 'bg-yellow-500';
	return 'bg-green-500';
}

/** VAS 0-100 → CSS color string for charts */
export function vasToHex(score: number): string {
	if (score < 25) return '#ef4444';
	if (score < 50) return '#f97316';
	if (score < 75) return '#eab308';
	return '#22c55e';
}
