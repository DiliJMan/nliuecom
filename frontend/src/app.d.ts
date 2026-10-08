import type { Schemas } from '#lib/api/client.ts';

declare global {
	namespace App {
		interface Locals {
			user: Schemas['Me'] | null;
		}
		interface PageData {
			user?: Schemas['Me'] | null;
		}
	}
}

export {};
