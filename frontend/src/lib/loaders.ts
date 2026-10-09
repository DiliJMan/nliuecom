import type { Page, Schemas } from '#lib/api/client.ts';
import { refSources, type Field, type Row } from '#lib/resources.ts';
import type { Option } from '#lib/components/MultiSelect.svelte';

type Fetch = typeof fetch;
export type Person = { id: string; email: string; name: string };

export async function getJson<T>(fetchFn: Fetch, path: string, fallback: T): Promise<T> {
	try {
		const response = await fetchFn(path);
		return response.ok ? ((await response.json()) as T) : fallback;
	} catch {
		return fallback;
	}
}

const emptyPage = <T>(): Page<T> => ({ count: 0, next: null, previous: null, results: [] });

/** Domains (in tree order) and the people list that pickers need on almost every page. */
export async function loadCommon(fetchFn: Fetch) {
	const [domains, people] = await Promise.all([
		getJson<Page<Schemas['Domain']>>(fetchFn, '/api/domains/?page_size=500', emptyPage()),
		getJson<Person[]>(fetchFn, '/api/auth/directory/', [])
	]);
	return { domains: domains.results, people };
}

/** Choices for the 'multi' and 'ref' fields named in `fields`. */
export async function loadRefs(fetchFn: Fetch, fields: Field[]): Promise<Record<string, Option[]>> {
	const keys = [...new Set(fields.filter((f) => f.ref).map((f) => f.ref as string))];
	const entries = await Promise.all(
		keys.map(async (key) => {
			const source = refSources[key];
			const page = await getJson<Page<Row>>(fetchFn, source.path, emptyPage());
			return [key, page.results.map((row) => ({ id: row.id as string, label: source.label(row) }))] as const;
		})
	);
	return Object.fromEntries(entries);
}

export async function loadPermissions(fetchFn: Fetch, domainId: string): Promise<string[]> {
	return getJson<string[]>(fetchFn, `/api/domains/${domainId}/effective_permissions/`, []);
}
