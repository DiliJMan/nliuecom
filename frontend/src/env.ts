import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	BACKEND_URL: {
		schema: (value) => (value ?? 'http://127.0.0.1:8000').replace(/\/$/, ''),
		description: 'Where the Django API listens. Only the server side of this app talks to it.'
	}
});
