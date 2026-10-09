import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { Schemas } from '#lib/api/client.ts';
import { getJson, loadCommon, loadPermissions } from '#lib/loaders.ts';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const response = await fetch(`/api/frameworks/${params.id}/`);
	if (!response.ok) error(response.status === 404 ? 404 : 403, 'Framework not available');
	const framework = (await response.json()) as Schemas['Framework'];
	const [nodes, common, permissions] = await Promise.all([
		getJson<Schemas['RequirementNode'][]>(fetch, `/api/frameworks/${params.id}/nodes/`, []),
		loadCommon(fetch),
		framework.domain ? loadPermissions(fetch, framework.domain) : Promise.resolve([] as string[])
	]);
	return { framework, nodes, ...common, permissions };
};
