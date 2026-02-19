/** "1月 15日 14:30" */
export function formatDateTime(iso: string): string {
	return new Date(iso).toLocaleString('ja-JP', {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

/** "2025年 1月 15日 14:30" */
export function formatFullDateTime(iso: string): string {
	return new Date(iso).toLocaleDateString('ja-JP', {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

/** "1月 15日" */
export function formatShortDate(iso: string): string {
	return new Date(iso).toLocaleDateString('ja-JP', {
		month: 'short',
		day: 'numeric'
	});
}

/** Today as "YYYY-MM-DD" (local timezone) */
export function todayISO(): string {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** N days ago as "YYYY-MM-DD" (local timezone) */
export function daysAgoISO(n: number): string {
	const d = new Date();
	d.setDate(d.getDate() - n);
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Hour at which the "health day" starts (JST) */
export const DAY_START_HOUR = 6;

/** True when current time is in overnight window (0:00–5:59) */
export function isOvernightHours(): boolean {
	return new Date().getHours() < DAY_START_HOUR;
}

/** "Effective today" — returns yesterday during overnight hours */
export function effectiveDateISO(): string {
	return isOvernightHours() ? daysAgoISO(1) : todayISO();
}

/** "Effective N days ago" — shifted by 1 during overnight hours */
export function effectiveDaysAgoISO(n: number): string {
	return daysAgoISO(isOvernightHours() ? n + 1 : n);
}
