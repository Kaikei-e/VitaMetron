import type { DivergenceDetection, DivergenceType } from '$lib/types/insights';

export interface DivergenceStyle {
	textColor: string;
	bgColor: string;
	badge: string;
}

const STYLES: Record<DivergenceType, DivergenceStyle> = {
	feeling_better_than_expected: {
		textColor: 'text-amber-600 dark:text-amber-400',
		bgColor: 'bg-amber-50 dark:bg-amber-900/20',
		badge: 'Feeling Better Than Expected'
	},
	feeling_worse_than_expected: {
		textColor: 'text-blue-600 dark:text-blue-400',
		bgColor: 'bg-blue-50 dark:bg-blue-900/20',
		badge: 'Feeling Worse Than Expected'
	},
	aligned: {
		textColor: 'text-green-600 dark:text-green-400',
		bgColor: 'bg-green-50 dark:bg-green-900/20',
		badge: 'Aligned'
	},
	no_condition_log: {
		textColor: 'text-gray-500',
		bgColor: 'bg-gray-100 dark:bg-gray-800',
		badge: 'No Condition Log'
	},
	no_biometric_data: {
		textColor: 'text-gray-500',
		bgColor: 'bg-gray-100 dark:bg-gray-800',
		badge: 'No Biometric Data'
	}
};

const DEFAULT_STYLE: DivergenceStyle = {
	textColor: 'text-gray-500',
	bgColor: 'bg-gray-100 dark:bg-gray-800',
	badge: ''
};

export function divergenceStyle(type: DivergenceType | string): DivergenceStyle {
	return STYLES[type as DivergenceType] ?? { ...DEFAULT_STYLE, badge: type };
}

export function filterValidDivergences(detections: DivergenceDetection[]): DivergenceDetection[] {
	return detections.filter(
		(d) => d.DivergenceType !== 'no_condition_log' && d.DivergenceType !== 'no_biometric_data'
	);
}
