import type { PageServerLoad } from './$types';
import type { Page, Schemas } from '#lib/api/client.ts';

const empty = <T>(): Page<T> => ({ count: 0, next: null, previous: null, results: [] });

export const load: PageServerLoad = async ({ fetch, parent }) => {
	const { user } = await parent();
	const get = async <T>(path: string): Promise<Page<T>> => {
		const response = await fetch(path);
		return response.ok ? ((await response.json()) as Page<T>) : empty<T>();
	};
	if (!user?.is_superuser) {
		return { roles: [], users: [], groups: [], domains: [], assignments: [], permissionTypes: [] };
	}
	const [roles, users, groups, domains, assignments, types] = await Promise.all([
		get<Schemas['Role']>('/api/roles/?page_size=500'),
		get<Schemas['User']>('/api/users/?page_size=500'),
		get<Schemas['UserGroup']>('/api/user-groups/?page_size=500'),
		get<Schemas['Domain']>('/api/domains/?page_size=500'),
		get<Schemas['RoleAssignment']>('/api/role-assignments/?page_size=500'),
		fetch('/api/object-types/').then((r) => (r.ok ? r.json() : []))
	]);
	return {
		roles: roles.results,
		users: users.results,
		groups: groups.results,
		domains: domains.results,
		assignments: assignments.results,
		permissionTypes: types as { key: string; label: string; actions: string[] }[]
	};
};
