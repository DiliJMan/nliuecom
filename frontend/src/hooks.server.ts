import { BACKEND_URL } from '$app/env/private';
import { sequence, type Handle } from '@sveltejs/kit/hooks';

const BACKEND = BACKEND_URL;
const BACKEND_ORIGIN = new URL(BACKEND).origin;
// Larger than the backend's upload limit, so Django still gives the precise error for files.
const MAX_BODY_BYTES = 40 * 1024 * 1024;

// Request headers that are safe and useful to pass to Django. Everything else is dropped.
const FORWARD_REQUEST = ['accept', 'content-type', 'cookie', 'x-csrftoken', 'user-agent'];

const jsonError = (status: number, detail: string) =>
	new Response(JSON.stringify({ detail }), { status, headers: { 'content-type': 'application/json' } });

/**
 * The browser only ever talks to this server. Calls under /api are passed on to Django, so the
 * session cookie stays first-party and HttpOnly, and Django never needs to allow cross-origin
 * requests. Nothing outside /api is forwarded.
 */
const proxyApi: Handle = async ({ event, resolve }) => {
	const { pathname, search } = event.url;
	if (!pathname.startsWith('/api/')) return resolve(event);

	const headers = new Headers();
	for (const name of FORWARD_REQUEST) {
		const value = event.request.headers.get(name);
		if (value) headers.set(name, value);
	}
	headers.set('origin', BACKEND_ORIGIN);
	headers.set('x-forwarded-for', event.getClientAddress());

	// The body is buffered, not streamed: it then goes out with a Content-Length, which every
	// Python server (including Django's development server) accepts. Chunked bodies are not.
	let body: ArrayBuffer | undefined;
	if (!['GET', 'HEAD'].includes(event.request.method)) {
		const declared = Number(event.request.headers.get('content-length') ?? 0);
		if (declared > MAX_BODY_BYTES) return jsonError(413, 'The request is too large.');
		body = await event.request.arrayBuffer();
		if (body.byteLength > MAX_BODY_BYTES) return jsonError(413, 'The request is too large.');
	}

	let upstream: Response;
	try {
		upstream = await fetch(`${BACKEND}${pathname}${search}`, {
			method: event.request.method,
			headers,
			body,
			redirect: 'manual'
		});
	} catch {
		return jsonError(502, 'The backend is not reachable.');
	}

	const out = new Headers();
	for (const name of ['content-type', 'content-disposition', 'x-content-type-options', 'content-security-policy', 'cache-control']) {
		const value = upstream.headers.get(name);
		if (value) out.set(name, value);
	}
	for (const cookie of upstream.headers.getSetCookie()) out.append('set-cookie', cookie);
	return new Response(upstream.body, { status: upstream.status, headers: out });
};

const securityHeaders: Handle = async ({ event, resolve }) => {
	const response = await resolve(event);
	response.headers.set('x-content-type-options', 'nosniff');
	response.headers.set('referrer-policy', 'same-origin');
	response.headers.set('x-frame-options', 'DENY');
	response.headers.set('permissions-policy', 'camera=(), microphone=(), geolocation=()');
	return response;
};

export const handle: Handle = sequence(securityHeaders, proxyApi);
