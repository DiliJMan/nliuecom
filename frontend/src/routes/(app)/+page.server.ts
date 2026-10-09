import type { PageServerLoad } from './$types';
import { getJson } from '#lib/loaders.ts';

type Dashboard = {
	assets: number;
	frameworks: number;
	controls: { total: number; by_status: Record<string, number> };
	risk: { scenarios: number; unrated: number; by_level: { name: string; colour: string; count: number }[] };
	compliance: {
		id: string; name: string; framework: string; domain: string;
		summary: { total: number; applicable: number; assessed_percent: number; compliant_percent: number };
	}[];
	tasks: { open: number; overdue: number; due_this_week: number };
};

export const load: PageServerLoad = async ({ fetch }) => ({
	dashboard: await getJson<Dashboard | null>(fetch, '/api/dashboard/', null)
});
