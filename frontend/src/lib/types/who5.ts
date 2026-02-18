/** Matches Go entity.WHO5Assessment */
export interface WHO5Assessment {
	ID: number;
	AssessedAt: string;
	PeriodStart: string;
	PeriodEnd: string;
	Items: number[];
	RawScore: number;
	Percentage: number;
	Note: string;
	CreatedAt: string;
}

export interface CreateWHO5Request {
	period_start: string;
	period_end: string;
	items: number[];
	note?: string;
}

export interface WHO5ListResult {
	items: WHO5Assessment[];
	total: number;
}
