<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { createApi } from '#lib/api/client.ts';

	let { data, children } = $props();

	const links = [
		{ href: '/', label: 'Domains' },
		{ href: '/access', label: 'Access' },
		{ href: '/audit', label: 'Audit log' }
	];

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
				<a href={link.href} aria-current={page.url.pathname === link.href ? 'page' : undefined}>{link.label}</a>
			{/each}
		</nav>
		<span class="muted">{data.user?.email}{data.user?.is_superuser ? ' (administrator)' : ''}</span>
		<button class="secondary" onclick={signOut}>Sign out</button>
	</div>
</header>
<main class="shell">{@render children()}</main>
