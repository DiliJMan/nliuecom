import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { Schemas } from '#lib/api/client.ts';
import { getJson, loadCommon, loadPermissions, loadRefs } from '#lib/loaders.ts';
import { resources, type Row } from '#lib/resources.ts';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const resource = resources[params.resource];
	if (!resource) error(404, 'Unknown page');
	const response = await fetch(`${resource.path}${params.id}/`);
	if (!response.ok) error(response.status === 404 ? 404 : 403, `${resource.label} not available`);
	const object = (await response.json()) as Row;
	const [common, refs, permissions, trail] = await Promise.all([
		loadCommon(fetch),
		loadRefs(fetch, resource.fields),
		loadPermissions(fetch, object.domain),
		getJson<Schemas['AuditEvent'][]>(fetch, `/api/audit/trail/${resource.objectType}/${params.id}/`, [])
	]);
	return { key: resource.key, object, ...common, refs, permissions, trail };
};
