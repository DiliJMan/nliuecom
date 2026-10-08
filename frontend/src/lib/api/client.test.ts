import { describe, expect, it, vi } from 'vitest';
import { ApiError, createApi } from './client.ts';

function jsonResponse(body: unknown, status = 200) {
	return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

describe('ApiError', () => {
	it('flattens field errors into readable strings', () => {
		const error = new ApiError(400, { name: ['This field is required.'], parent: 'Bad parent' });
		expect(error.fields).toEqual({ name: 'This field is required.', parent: 'Bad parent' });
	});

	it('prefers the server detail, then falls back by status', () => {
		expect(new ApiError(409, { detail: 'Still referenced.' }).message).toBe('Still referenced.');
		expect(new ApiError(403, null).message).toMatch(/permission/);
		expect(new ApiError(404, null).message).toBe('Not found.');
	});
});

describe('createApi', () => {
	it('fetches a CSRF token before the first write and sends it as a header', async () => {
		const fetchFn = vi
			.fn()
			.mockResolvedValueOnce(jsonResponse({ csrfToken: 'token-123' }))
			.mockResolvedValueOnce(jsonResponse({ id: '1' }, 201));
		const api = createApi(fetchFn as unknown as typeof fetch);
		await api.post('/api/domains/', { name: 'Finance' });
		expect(fetchFn.mock.calls[0][0]).toBe('/api/auth/csrf/');
		const [, init] = fetchFn.mock.calls[1];
		expect(init.method).toBe('POST');
		expect(init.headers['x-csrftoken']).toBe('token-123');
		expect(JSON.parse(init.body)).toEqual({ name: 'Finance' });
	});

	it('sends a JSON content type even when a write has no payload', async () => {
		const fetchFn = vi
			.fn()
			.mockResolvedValueOnce(jsonResponse({ csrfToken: 't' }))
			.mockResolvedValueOnce(new Response(null, { status: 204 }));
		await createApi(fetchFn as unknown as typeof fetch).post('/api/auth/logout/');
		const [, init] = fetchFn.mock.calls[1];
		expect(init.headers['content-type']).toBe('application/json');
		expect(init.body).toBe('{}');
	});

	it('does not ask for a token on reads', async () => {
		const fetchFn = vi.fn().mockResolvedValue(jsonResponse([]));
		await createApi(fetchFn as unknown as typeof fetch).get('/api/domains/');
		expect(fetchFn).toHaveBeenCalledTimes(1);
	});

	it('throws ApiError with the server body on failure and returns undefined for 204', async () => {
		const fail = vi.fn().mockResolvedValue(jsonResponse({ detail: 'nope' }, 403));
		await expect(createApi(fail as unknown as typeof fetch).get('/api/x/')).rejects.toMatchObject({ status: 403 });
		const empty = vi
			.fn()
			.mockResolvedValueOnce(jsonResponse({ csrfToken: 't' }))
			.mockResolvedValueOnce(new Response(null, { status: 204 }));
		expect(await createApi(empty as unknown as typeof fetch).delete('/api/domains/1/')).toBeUndefined();
	});
});
