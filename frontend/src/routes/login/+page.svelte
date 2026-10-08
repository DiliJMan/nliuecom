<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { ApiError, createApi } from '#lib/api/client.ts';

	let email = $state('');
	let password = $state('');
	let message = $state('');
	let busy = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		message = '';
		try {
			await createApi().post('/api/auth/login/', { email, password });
			await invalidateAll();
			await goto('/');
		} catch (error) {
			message = error instanceof ApiError && error.status === 401
				? 'The email or password is wrong, or the account is temporarily locked.'
				: 'Sign-in failed. Try again in a moment.';
		} finally {
			busy = false;
			password = '';
		}
	}
</script>

<svelte:head><title>Sign in</title></svelte:head>

<main class="shell" style="max-width: 420px; padding-top: 12vh">
	<h1>nliuecom</h1>
	<p class="muted">Governance, risk and compliance workspace.</p>
	<form class="card" onsubmit={submit}>
		<label for="email">Email</label>
		<input id="email" type="email" autocomplete="username" required bind:value={email} />
		<label for="password">Password</label>
		<input id="password" type="password" autocomplete="current-password" required bind:value={password} />
		<p class="error" role="alert" aria-live="polite">{message}</p>
		<button type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
	</form>
</main>
