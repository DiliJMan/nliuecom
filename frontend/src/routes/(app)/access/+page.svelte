<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { ApiError, createApi } from '#lib/api/client.ts';

	let { data } = $props();

	let subjectKind = $state<'user' | 'group'>('user');
	let subject = $state('');
	let role = $state('');
	let domain = $state('');
	let recursive = $state(true);
	let message = $state('');

	async function assign(event: SubmitEvent) {
		event.preventDefault();
		message = '';
		try {
			await createApi().post('/api/role-assignments/', { [subjectKind]: subject, role, domain, recursive });
			subject = '';
			await invalidateAll();
		} catch (error) {
			message = error instanceof ApiError ? Object.values(error.fields).join(' ') || error.message : 'Could not assign the role.';
		}
	}

	async function revoke(id: string) {
		await createApi().delete(`/api/role-assignments/${id}/`);
		await invalidateAll();
	}
</script>

<svelte:head><title>Access</title></svelte:head>

<h1 style="margin-top: 20px">Access</h1>

<section class="card">
	<h2>Your roles</h2>
	{#if data.user?.is_superuser}
		<p>You are an instance administrator, so every domain and action is open to you.</p>
	{:else if data.user?.grants.length}
		<table>
			<thead><tr><th>Role</th><th>Domain</th><th>Reaches</th></tr></thead>
			<tbody>
				{#each data.user.grants as grant (grant.id)}
					<tr><td>{grant.role_name}</td><td><a href="/domains/{grant.domain}">{grant.domain_name}</a></td><td>{grant.recursive ? 'Domain and sub-domains' : 'This domain only'}</td></tr>
				{/each}
			</tbody>
		</table>
	{:else}<p class="muted">You have no roles yet.</p>{/if}
</section>

{#if data.user?.is_superuser}
	<section class="card">
		<h2>Assign a role</h2>
		<form onsubmit={assign}>
			<div class="row">
				<div>
					<label for="kind">Assign to</label>
					<select id="kind" bind:value={subjectKind} onchange={() => (subject = '')}>
						<option value="user">A user</option><option value="group">A group</option>
					</select>
				</div>
				<div>
					<label for="subject">{subjectKind === 'user' ? 'User' : 'Group'}</label>
					<select id="subject" required bind:value={subject}>
						<option value="" disabled>Choose…</option>
						{#each subjectKind === 'user' ? data.users : data.groups as s (s.id)}
							<option value={s.id}>{'email' in s ? s.email : s.name}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="role">Role</label>
					<select id="role" required bind:value={role}>
						<option value="" disabled>Choose…</option>
						{#each data.roles as r (r.id)}<option value={r.id}>{r.name}</option>{/each}
					</select>
				</div>
				<div>
					<label for="domain">Domain</label>
					<select id="domain" required bind:value={domain}>
						<option value="" disabled>Choose…</option>
						{#each data.domains as d (d.id)}<option value={d.id}>{' '.repeat(d.depth * 3)}{d.name}</option>{/each}
					</select>
				</div>
			</div>
			<label><input type="checkbox" bind:checked={recursive} /> Also applies to every sub-domain</label>
			<p class="error" role="status">{message}</p>
			<button type="submit">Assign</button>
		</form>
	</section>

	<section class="card">
		<h2>Current assignments</h2>
		<table>
			<thead><tr><th>Who</th><th>Role</th><th>Domain</th><th>Reach</th><th></th></tr></thead>
			<tbody>
				{#each data.assignments as a (a.id)}
					<tr>
						<td>{a.user_email ?? `${a.group_name} (group)`}</td><td>{a.role_name}</td>
						<td>{a.domain_name}</td><td>{a.recursive ? 'with sub-domains' : 'this domain only'}</td>
						<td><button class="danger" onclick={() => revoke(a.id)}>Remove</button></td>
					</tr>
				{:else}
					<tr><td colspan="5" class="muted">No assignments yet.</td></tr>
				{/each}
			</tbody>
		</table>
	</section>

	<section class="card">
		<h2>Roles</h2>
		<table>
			<thead><tr><th>Name</th><th>Kind</th><th>Permissions</th></tr></thead>
			<tbody>
				{#each data.roles as r (r.id)}
					<tr><td>{r.name}<div class="muted">{r.description}</div></td><td>{r.builtin ? 'Built in' : 'Custom'}</td><td>{r.permissions?.length ?? 0}</td></tr>
				{/each}
			</tbody>
		</table>
		<p class="muted">Custom roles can be created through the API today. A visual role editor comes next.</p>
	</section>
{/if}
