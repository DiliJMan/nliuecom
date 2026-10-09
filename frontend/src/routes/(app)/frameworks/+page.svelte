<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { ApiError, createApi, type Schemas } from '#lib/api/client.ts';
	import ResourceForm from '#lib/components/ResourceForm.svelte';
	import { frameworkResource } from '#lib/resources.ts';

	let { data } = $props();
	const user = $derived(data.user);
	const domainName = $derived(new Map(data.domains.map((d) => [d.id, d.name])));
	let creating = $state(false);

	const kinds = [
		{ value: 'scf', label: 'Secure Controls Framework workbook (.xlsx)', accept: '.xlsx' },
		{ value: 'iso27001', label: 'ISO/IEC 27001:2022, your licensed PDF (.pdf)', accept: '.pdf' },
		{ value: 'project', label: 'Project framework file (.json)', accept: '.json' }
	];
	let kind = $state('scf');
	let replace = $state(false);
	let importDomain = $state('');
	let file = $state<File | null>(null);
	let busy = $state(false);
	let message = $state('');
	let ok = $state(false);

	async function importFile(event: SubmitEvent) {
		event.preventDefault();
		if (!file) return;
		busy = true;
		message = '';
		ok = false;
		try {
			const form = new FormData();
			form.append('kind', kind);
			form.append('file', file);
			form.append('replace', String(replace));
			if (kind === 'project' && importDomain) form.append('domain', importDomain);
			const framework = await createApi().post<Schemas['Framework'] & { notes?: string[] }>('/api/frameworks/import/', form);
			ok = true;
			message = `Loaded ${framework.name} ${framework.version}: ${framework.assessable_count} assessable requirements.${framework.notes?.length ? ' ' + framework.notes.join(' ') : ''}`;
			file = null;
			await invalidateAll();
		} catch (error) {
			message = error instanceof ApiError ? Object.values(error.fields).join(' ') || error.message : 'The import failed.';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>Frameworks</title></svelte:head>

<h1 style="margin-top: 20px">Frameworks</h1>
<p class="muted">Catalogues of requirements and controls that assessments run against. Imported frameworks are read-only; derive a copy to adapt one to your organisation.</p>

<section class="card">
	{#if data.frameworks.length}
		<table>
			<thead><tr><th scope="col">Framework</th><th scope="col">Provider</th><th scope="col">Requirements</th><th scope="col">Kind</th><th scope="col">Use</th></tr></thead>
			<tbody>
				{#each data.frameworks as f (f.id)}
					<tr>
						<td><a href="/frameworks/{f.id}">{f.name}</a> <span class="muted">{f.version}</span></td>
						<td>{f.provider}</td>
						<td>{f.assessable_count}</td>
						<td>{f.domain ? `Custom, ${domainName.get(f.domain) ?? 'a domain'}` : 'Imported'}</td>
						<td>{#if f.redistributable}<span class="chip">Open</span>{:else}<span class="chip" title={f.licence_note}>Licensed, stays here</span>{/if}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<p class="muted">No frameworks yet. {user?.is_superuser ? 'Import one below.' : 'Ask an administrator to import one.'}</p>
	{/if}
</section>

{#if user?.is_superuser}
	<section class="card">
		<h2>Import a framework</h2>
		<p class="muted">
			Use files you hold yourself. Licensed standards and the Secure Controls Framework are read into this installation's database only. They are never added to the source code, and they cannot be exported from here.
		</p>
		<form onsubmit={importFile}>
			<label for="kind">Source</label>
			<select id="kind" bind:value={kind}>{#each kinds as k (k.value)}<option value={k.value}>{k.label}</option>{/each}</select>
			<label for="file">File</label>
			<input id="file" type="file" accept={kinds.find((k) => k.value === kind)?.accept} onchange={(e) => (file = e.currentTarget.files?.[0] ?? null)} />
			{#if kind === 'project'}
				<label for="import-domain">Into a domain (optional)</label>
				<select id="import-domain" bind:value={importDomain}>
					<option value="">Instance-wide, read-only</option>
					{#each data.domains as d (d.id)}<option value={d.id}>{' '.repeat((d.depth ?? 0) * 3)}{d.name}</option>{/each}
				</select>
			{/if}
			<label><input type="checkbox" bind:checked={replace} /> Replace the framework if it is already loaded</label>
			<p class={ok ? 'ok' : 'error'} role="status" aria-live="polite">{message}</p>
			<button type="submit" disabled={busy || !file}>{busy ? 'Importing…' : 'Import'}</button>
		</form>
	</section>
{/if}

<section class="card">
	<div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
		<h2 style="margin: 0">Your own framework</h2>
		<button class="secondary" onclick={() => (creating = !creating)} aria-expanded={creating}>{creating ? 'Close form' : 'New custom framework'}</button>
	</div>
	{#if creating}
		<ResourceForm
			resource={frameworkResource}
			domains={data.domains}
			people={[]}
			refs={{}}
			onsaved={(row) => goto(`/frameworks/${row.id}`)}
		/>
	{/if}
</section>
