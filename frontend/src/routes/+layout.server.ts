import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import type { Schemas } from '#lib/api/client.ts';

export const load: LayoutServerLoad = async ({ fetch, url }) => {
	const response = await fetch('/api/auth/me/');
	if (response.ok) {
		const user = (await response.json()) as Schemas['Me'];
		if (url.pathname === '/login') redirect(303, '/');
		return { user };
	}
	if (url.pathname !== '/login') redirect(303, '/login');
	return { user: null };
};
