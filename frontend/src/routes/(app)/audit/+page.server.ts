import type { PageServerLoad } from './$types';
import type { Page, Schemas } from '#lib/api/client.ts';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const query = new URLSearchParams({ page_size: '50' });
	for (const key of ['page', 'object_type', 'action']) {
		const value = url.searchParams.get(key);
		if (value) query.set(key, value);
	}
	const [events, types] = await Promise.all([
		fetch(`/api/audit/?${query}`),
		fetch('/api/object-types/')
	]);
	return {
		events: events.ok
			? ((await events.json()) as Page<Schemas['AuditEvent']>)
			: { count: 0, next: null, previous: null, results: [] },
		objectTypes: types.ok ? ((await types.json()) as { key: string; label: string }[]) : [],
		filters: { object_type: url.searchParams.get('object_type') ?? '', action: url.searchParams.get('action') ?? '' },
		page: Number(url.searchParams.get('page') ?? 1)
	};
};
