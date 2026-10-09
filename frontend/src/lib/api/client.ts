import type { components } from './schema';

export type Schemas = components['schemas'];

export class ApiError extends Error {
	constructor(
		readonly status: number,
		readonly body: unknown
	) {
		super(describe(body, status));
	}
	/** Field-level messages, when the server gave any. */
	get fields(): Record<string, string> {
		if (!this.body || typeof this.body !== 'object') return {};
		return Object.fromEntries(
			Object.entries(this.body as Record<string, unknown>).map(([k, v]) => [
				k,
				Array.isArray(v) ? v.join(' ') : typeof v === 'string' ? v : JSON.stringify(v)
			])
		);
	}
}

function describe(body: unknown, status: number): string {
	if (body && typeof body === 'object' && 'detail' in body) return String((body as { detail: unknown }).detail);
	if (status === 403) return 'You do not have permission to do that.';
	if (status === 404) return 'Not found.';
	return `Request failed (${status}).`;
}

function readCookie(name: string): string | null {
	if (typeof document === 'undefined') return null;
	const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`));
	return match ? decodeURIComponent(match.split('=')[1]) : null;
}

type Fetch = typeof fetch;

export function createApi(fetchFn: Fetch = fetch) {
	async function csrfToken(): Promise<string> {
		const existing = readCookie('csrftoken');
		if (existing) return existing;
		const response = await fetchFn('/api/auth/csrf/');
		return (await response.json()).csrfToken;
	}

	async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
		const headers: Record<string, string> = { accept: 'application/json' };
		if (method !== 'GET') headers['x-csrftoken'] = await csrfToken();
		let payload: BodyInit | undefined;
		if (body instanceof FormData) payload = body;
		else if (body !== undefined || method !== 'GET') {
			// Writes always carry a JSON body. A body-less POST has no content type, and
			// SvelteKit's cross-site form protection rejects those.
			headers['content-type'] = 'application/json';
			payload = JSON.stringify(body ?? {});
		}
		const response = await fetchFn(path, { method, headers, body: payload });
		if (response.status === 204) return undefined as T;
		const text = await response.text();
		const data = text ? JSON.parse(text) : null;
		if (!response.ok) throw new ApiError(response.status, data);
		return data as T;
	}

	return {
		get: <T>(path: string) => request<T>('GET', path),
		post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
		patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
		delete: (path: string) => request<void>('DELETE', path)
	};
}

export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };
