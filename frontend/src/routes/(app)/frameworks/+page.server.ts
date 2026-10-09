import type { PageServerLoad } from './$types';
import type { Page, Schemas } from '#lib/api/client.ts';
import { getJson, loadCommon } from '#lib/loaders.ts';

export const load: PageServerLoad = async ({ fetch }) => {
	const [list, common] = await Promise.all([
		getJson<Page<Schemas['Framework']>>(fetch, '/api/frameworks/?page_size=200', { count: 0, next: null, previous: null, results: [] }),
		loadCommon(fetch)
	]);
	return { frameworks: list.results, ...common };
};
