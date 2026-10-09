<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { ApiError, createApi } from '#lib/api/client.ts';
	import DomainForm from '#lib/components/DomainForm.svelte';
	import History from '#lib/components/History.svelte';

	let { data } = $props();

	const can = (action: string) => data.permissions.includes(`domains.domain:${action}`);

	let childName = $state('');
	let childKind = $state('team');
	let childMessage = $state('');

	async function addChild(event: SubmitEvent) {
		event.preventDefault();
		childMessage = '';
		try {
			await createApi().post('/api/domains/', { name: childName, kind: childKind, parent: data.domain.id });
			childName = '';
			await invalidateAll();
		} catch (error) {
			childMessage = error instanceof ApiError ? Object.values(error.fields).join(' ') || error.message : 'Could not add the domain.';
		}
	}
</script>

<svelte:head><title>{data.domain.name}</title></svelte:head>

<p class="muted" style="margin-top: 20px">
	<a href="/domains">Domains</a>
	{#each data.breadcrumb as ancestor (ancestor.id)} / <a href="/domains/{ancestor.id}">{ancestor.name}</a>{/each}
</p>
<h1>{data.domain.name}</h1>

{#key data.domain.id}
	<DomainForm domain={data.domain} fields={data.fields} canChange={can('change')} canDelete={can('delete')} />
{/key}

<div class="grid">
	<section class="card">
		<h2>Sub-domains</h2>
		{#if data.children.length}
			<ul>{#each data.children as child (child.id)}<li><a href="/domains/{child.id}">{child.name}</a></li>{/each}</ul>
		{:else}<p class="muted">None yet.</p>{/if}
		{#if can('add')}
			<form class="row" onsubmit={addChild}>
				<div><label for="child-name">New sub-domain</label><input id="child-name" required bind:value={childName} /></div>
				<div>
					<label for="child-kind">Type</label>
					<select id="child-kind" bind:value={childKind}>
						<option value="subsidiary">Subsidiary</option><option value="business_unit">Business unit</option>
						<option value="entity">Entity</option><option value="team">Team</option><option value="other">Other</option>
					</select>
				</div>
				<button type="submit">Add</button>
			</form>
			<p class="error" role="status">{childMessage}</p>
		{/if}
	</section>

	<section class="card">
		<h2>Who has access here</h2>
		{#if data.permissions.includes('access.roleassignment:view')}
			{#if data.assignments.length}
				<ul>{#each data.assignments as a (a.id)}<li><span class="mono">{a.user_email ?? a.group_name}</span> · {a.role_name} {a.recursive ? '(includes sub-domains)' : '(this domain only)'}</li>{/each}</ul>
			{:else}<p class="muted">No direct assignments. Access may be inherited from a parent domain.</p>{/if}
		{:else}<p class="muted">Your role does not include viewing assignments.</p>{/if}
		<p><a href="/access">Manage access</a></p>
	</section>
</div>

<section class="card">
	<h2>History</h2>
	<History events={data.trail} />
</section>
