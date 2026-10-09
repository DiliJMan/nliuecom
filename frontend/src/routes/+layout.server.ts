import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import type { Schemas } from '#lib/api/client.ts';

type About = { name: string; licence: string; licence_url: string; source_url: string };

export const load: LayoutServerLoad = async ({ fetch, url }) => {
	const aboutResponse = await fetch('/api/about/');
	const about = aboutResponse.ok ? ((await aboutResponse.json()) as About) : null;
	const response = await fetch('/api/auth/me/');
	if (response.ok) {
		const user = (await response.json()) as Schemas['Me'];
		if (url.pathname === '/login') redirect(303, '/');
		return { user, about };
	}
	if (url.pathname !== '/login') redirect(303, '/login');
	return { user: null, about };
};
