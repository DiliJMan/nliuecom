import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { Page, Schemas } from '#lib/api/client.ts';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const id = params.id;
	const get = async <T>(path: string, fallback: T): Promise<T> => {
		const response = await fetch(path);
		return response.ok ? ((await response.json()) as T) : fallback;
	};

	const domainResponse = await fetch(`/api/domains/${id}/`);
	if (!domainResponse.ok) error(domainResponse.status === 404 ? 404 : 403, 'Domain not available');
	const domain = (await domainResponse.json()) as Schemas['Domain'];

	const [permissions, trail, fields, domains, assignments] = await Promise.all([
		get<string[]>(`/api/domains/${id}/effective_permissions/`, []),
		get<Schemas['AuditEvent'][]>(`/api/audit/trail/domains.domain/${id}/`, []),
		get<Page<Schemas['CustomFieldDefinition']>>(
			`/api/custom-fields/?object_type=domains.domain&domain=${id}`,
			{ count: 0, next: null, previous: null, results: [] }
		),
		get<Page<Schemas['Domain']>>('/api/domains/?page_size=500', { count: 0, next: null, previous: null, results: [] }),
		get<Page<Schemas['RoleAssignment']>>(`/api/role-assignments/?domain=${id}`, {
			count: 0,
			next: null,
			previous: null,
			results: []
		})
	]);

	const byId = new Map(domains.results.map((d) => [d.id, d]));
	const breadcrumb = domain.path
		.split('/')
		.filter(Boolean)
		.slice(0, -1)
		.map((pathId) => byId.get(pathId))
		.filter((d): d is Schemas['Domain'] => Boolean(d));

	return {
		domain,
		permissions,
		trail,
		fields: fields.results,
		breadcrumb,
		children: domains.results.filter((d) => d.parent === id),
		assignments: assignments.results
	};
};
