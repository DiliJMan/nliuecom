import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// The public address of the web app, fixed at build time. SvelteKit compares it with the Origin
// header of every write, so it must match what the browser shows (use https:// behind TLS).
const origin = process.env.NLIUE_WEB_ORIGIN;

// SvelteKit 3 reads its options from the plugin call, not from svelte.config.js.
export default defineConfig({
	plugins: [
		sveltekit({
			adapter: adapter(),
			paths: origin ? { origin } : {},
			csp: {
				mode: 'auto',
				directives: {
					'default-src': ['self'],
					'script-src': ['self'],
					'style-src': ['self', 'unsafe-inline'],
					'img-src': ['self', 'data:'],
					'connect-src': ['self'],
					'object-src': ['none'],
					'base-uri': ['self'],
					'frame-ancestors': ['none'],
					'form-action': ['self']
				}
			}
		})
	],
	test: { include: ['src/**/*.test.ts'] }
});
