import type { PageServerLoad } from './$types';
import type { TreeNode } from '#lib/components/DomainTree.svelte';

export const load: PageServerLoad = async ({ fetch }) => {
	const response = await fetch('/api/domains/tree/');
	return { tree: response.ok ? ((await response.json()) as TreeNode[]) : [] };
};
