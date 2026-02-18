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

/** Today as "YYYY-MM-DD" */
export function todayISO(): string {
	return new Date().toISOString().slice(0, 10);
}

/** N days ago as "YYYY-MM-DD" */
export function daysAgoISO(n: number): string {
	return new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);
}
