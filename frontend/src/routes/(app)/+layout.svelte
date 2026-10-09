<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { createApi } from '#lib/api/client.ts';

	let { data, children } = $props();

	const links = [
		{ href: '/', label: 'Dashboard' },
		{ href: '/domains', label: 'Domains' },
		{ href: '/r/assets', label: 'Assets' },
		{ href: '/r/risk-assessments', label: 'Risk' },
		{ href: '/r/applied-controls', label: 'Controls' },
		{ href: '/r/evidence', label: 'Evidence' },
		{ href: '/r/compliance-assessments', label: 'Compliance' },
		{ href: '/frameworks', label: 'Frameworks' },
		{ href: '/r/tasks', label: 'Tasks' },
		{ href: '/access', label: 'Access' },
		{ href: '/audit', label: 'Audit log' }
	];
	// A section stays highlighted on its detail pages as well as its list.
	const current = (href: string) =>
		href === '/' ? page.url.pathname === '/' : page.url.pathname === href || page.url.pathname.startsWith(`${href}/`);
	const sections: Record<string, string> = { '/risk': '/r/risk-assessments', '/compliance': '/r/compliance-assessments' };
	const highlighted = (href: string) =>
		current(href) || Object.entries(sections).some(([prefix, target]) => target === href && page.url.pathname.startsWith(`${prefix}/`));

	async function signOut() {
		await createApi().post('/api/auth/logout/');
		await invalidateAll();
		await goto('/login');
	}
</script>

<header class="bar">
	<div class="shell">
		<a class="brand" href="/">nliuecom</a>
		<nav aria-label="Main">
			{#each links as link (link.href)}
				<a href={link.href} aria-current={highlighted(link.href) ? 'page' : undefined}>{link.label}</a>
			{/each}
		</nav>
		<span class="muted">{data.user?.email}{data.user?.is_superuser ? ' (administrator)' : ''}</span>
		<button class="secondary" onclick={signOut}>Sign out</button>
	</div>
</header>
<main class="shell">{@render children()}</main>
