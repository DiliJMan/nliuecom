import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { Page } from '#lib/api/client.ts';
import { loadCommon, loadRefs, getJson } from '#lib/loaders.ts';
import { resources, type Row } from '#lib/resources.ts';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const resource = resources[params.resource];
	if (!resource) error(404, 'Unknown page');
	const query = new URLSearchParams({ page_size: '50' });
	for (const key of ['page', 'search', 'ordering', 'domain', ...(resource.filters ?? []).map((f) => f.key)]) {
		const value = url.searchParams.get(key);
		if (value) query.set(key, value);
	}
	const [list, common, refs] = await Promise.all([
		getJson<Page<Row>>(fetch, `${resource.path}?${query}`, { count: 0, next: null, previous: null, results: [] }),
		loadCommon(fetch),
		loadRefs(fetch, resource.fields)
	]);
	return {
		key: resource.key,
		list,
		...common,
		refs,
		page: Number(url.searchParams.get('page') ?? 1),
		active: Object.fromEntries(
			['search', 'ordering', 'domain', ...(resource.filters ?? []).map((f) => f.key)].map((k) => [k, url.searchParams.get(k) ?? ''])
		)
	};
};
