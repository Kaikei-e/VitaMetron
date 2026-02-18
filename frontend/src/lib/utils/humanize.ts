const featureNames: Record<string, string> = {
	hrv_daily_rmssd: 'HRV (daily)',
	hrv_deep_rmssd: 'HRV (deep sleep)',
	sleep_duration: 'Sleep Duration',
	sleep_deep_min: 'Deep Sleep',
	sleep_rem_min: 'REM Sleep',
	sleep_light_min: 'Light Sleep',
	sleep_onset_latency: 'Sleep Onset',
	resting_hr: 'Resting HR',
	steps: 'Steps',
	active_zone_min: 'Active Zone Minutes',
	calories_active: 'Active Calories',
	spo2_avg: 'SpO2',
	br_full_sleep: 'Breathing Rate',
	skin_temp_variation: 'Skin Temperature',
	vo2_max: 'VO2 Max',
	sri_value: 'Sleep Regularity',
	z_ln_rmssd: 'HRV Z-score',
	z_resting_hr: 'Resting HR Z-score',
	z_sleep_duration: 'Sleep Duration Z-score',
	z_sri: 'SRI Z-score',
	z_spo2: 'SpO2 Z-score',
	z_deep_sleep: 'Deep Sleep Z-score',
	z_br: 'Breathing Rate Z-score',
	condition_overall: 'Condition Score',
	condition_mental: 'Mental Score',
	condition_physical: 'Physical Score',
	condition_energy: 'Energy Score'
};

/** VRI contributing_factors metric names → Japanese labels */
const vriMetricNames: Record<string, string> = {
	ln_rmssd: 'HRV',
	resting_hr: '安静時心拍',
	sleep_duration: '睡眠時間',
	sri: '睡眠規則性',
	spo2: 'SpO2',
	deep_sleep: '深い睡眠',
	br: '呼吸数'
};

export function humanizeVRIMetric(metric: string): string {
	return vriMetricNames[metric] ?? metric;
}

export function humanizeFeature(feature: string): string {
	return featureNames[feature] ?? feature.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
