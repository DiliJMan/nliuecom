<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { ApiError, createApi, type Schemas } from '#lib/api/client.ts';
	import ResourceForm from '#lib/components/ResourceForm.svelte';
	import { frameworkResource, nodeResource, type Row } from '#lib/resources.ts';

	type Node = Schemas['RequirementNode'];
	let { data } = $props();
	const fw = $derived(data.framework);
	const custom = $derived(fw.domain !== null && fw.domain !== undefined);
	const can = (action: string, type: string) => data.permissions.includes(`${type}:${action}`);
	const canEdit = $derived(custom && !fw.locked && can('change', 'frameworks.requirementnode'));

	let open = $state<Record<string, boolean>>({});
	let search = $state('');
	let selected = $state<Node | 'new' | null>(null);
	let deriveName = $state('');
	let deriveDomain = $state('');
	let deriveMessage = $state('');

	const children = $derived.by(() => {
		const map = new Map<string | null, Node[]>();
		for (const n of data.nodes) map.set(n.parent ?? null, [...(map.get(n.parent ?? null) ?? []), n]);
		return map;
	});
	const matches = $derived(
		search.trim() === '' ? [] : data.nodes.filter((n) => `${n.ref_id} ${n.name} ${n.description ?? ''}`.toLowerCase().includes(search.trim().toLowerCase()))
	);
	const parents = $derived({
		parents: data.nodes.filter((n) => selected === 'new' || n.id !== (selected as Node | null)?.id).map((n) => ({ id: n.id as string, label: `${n.ref_id} ${n.name}` }))
	});

	async function derive(event: SubmitEvent) {
		event.preventDefault();
		deriveMessage = '';
		try {
			const copy = await createApi().post<Schemas['Framework']>(`/api/frameworks/${fw.id}/derive/`, { domain: deriveDomain, name: deriveName });
			await goto(`/frameworks/${copy.id}`);
		} catch (error) {
			deriveMessage = error instanceof ApiError ? Object.values(error.fields).join(' ') || error.message : 'Could not derive the framework.';
		}
	}

	async function removeNode(node: Node) {
		if (!confirm(`Delete ${node.ref_id} and everything beneath it?`)) return;
		await createApi().delete(`/api/requirement-nodes/${node.id}/`);
		selected = null;
		await invalidateAll();
	}
	async function removeFramework() {
		if (!confirm('Delete this framework? Assessments that use it block the deletion.')) return;
		await createApi().delete(`/api/frameworks/${fw.id}/`);
		await goto('/frameworks');
	}
</script>

{#snippet branch(parent: string | null)}
	<ul class="tree">
		{#each children.get(parent) ?? [] as n (n.id)}
			{@const kids = children.get(n.id)}
			<li>
				{#if kids?.length}
					<button class="twisty" aria-expanded={!!open[n.id]} aria-label="{open[n.id] ? 'Collapse' : 'Expand'} {n.ref_id}" onclick={() => (open[n.id] = !open[n.id])}>{open[n.id] ? '▾' : '▸'}</button>
				{:else}<span class="twisty"></span>{/if}
				<button class="rowbtn" onclick={() => { selected = n; if (kids?.length) open[n.id] = !open[n.id]; }}><span class="mono">{n.ref_id}</span> {n.name}</button>
				{#if !n.assessable}<span class="chip">heading</span>{/if}
				{#if open[n.id] && kids?.length}{@render branch(n.id)}{/if}
			</li>
		{/each}
	</ul>
{/snippet}

<svelte:head><title>{fw.name}</title></svelte:head>

<p class="muted" style="margin-top: 20px"><a href="/frameworks">Frameworks</a></p>
<h1>{fw.name} <span class="muted" style="font-size: 1rem">{fw.version}</span></h1>
<p class="muted">{fw.provider}{fw.provider && fw.description ? ' · ' : ''}{fw.description}</p>

{#if fw.licence_note || fw.attribution}
	<section class="card" aria-label="Licence">
		{#if fw.licence_note}<p style="margin-top: 0">{fw.licence_note}</p>{/if}
		{#if fw.attribution}<p class="muted" style="margin-bottom: 0">{fw.attribution}</p>{/if}
		{#if fw.source}<p class="muted" style="margin-bottom: 0">Source: {fw.source}</p>{/if}
	</section>
{/if}

<div class="grid">
	<section class="card">
		<h2>Use it</h2>
		<p><strong>{fw.assessable_count}</strong> assessable requirements, {fw.node_count} entries in all.</p>
		<p><a href="/r/compliance-assessments">Start a compliance assessment</a></p>
		{#if fw.redistributable}<p><a href="/api/frameworks/{fw.id}/export/" download>Export as a project file</a></p>{:else}<p class="muted">Export is switched off for licensed content.</p>{/if}
	</section>
	<section class="card">
		<h2>Derive your own copy</h2>
		<form onsubmit={derive}>
			<label for="d-name">Name</label><input id="d-name" required bind:value={deriveName} />
			<label for="d-domain">Owning domain</label>
			<select id="d-domain" required bind:value={deriveDomain}>
				<option value="" disabled>Choose…</option>
				{#each data.domains as d (d.id)}<option value={d.id}>{' '.repeat((d.depth ?? 0) * 3)}{d.name}</option>{/each}
			</select>
			<p class="error" role="status">{deriveMessage}</p>
			<button type="submit">Derive</button>
		</form>
	</section>
</div>

{#if custom}
	<section class="card">
		<h2>Framework details</h2>
		{#key fw.id}
			<ResourceForm resource={frameworkResource} object={fw as unknown as Row} domains={data.domains} people={[]} refs={{}} canChange={can('change', 'frameworks.framework')} canDelete={can('delete', 'frameworks.framework')} onsaved={() => invalidateAll()} ondeleted={removeFramework} />
		{/key}
	</section>
{/if}

<section class="card">
	<div style="display: flex; justify-content: space-between; gap: 12px; align-items: end; flex-wrap: wrap">
		<div style="flex: 1; min-width: 220px"><label for="fw-search">Search requirements</label><input id="fw-search" type="search" bind:value={search} /></div>
		{#if canEdit}<button onclick={() => (selected = 'new')}>Add a requirement</button>{/if}
	</div>
	<div class="scroll">
		{#if search.trim()}
			<p class="muted">{matches.length} match{matches.length === 1 ? '' : 'es'}</p>
			<ul class="tree">{#each matches.slice(0, 200) as n (n.id)}<li><button class="rowbtn" onclick={() => (selected = n)}><span class="mono">{n.ref_id}</span> {n.name}</button></li>{/each}</ul>
		{:else}
			{@render branch(null)}
		{/if}
	</div>
</section>

{#if selected}
	{#key selected === 'new' ? 'new' : selected.id}
		<section class="card" aria-label="Requirement">
			{#if selected === 'new'}
				<h2>New requirement</h2>
			{:else}
				<h2><span class="mono">{selected.ref_id}</span> {selected.name}</h2>
				{#if !canEdit && selected.description}<p style="white-space: pre-wrap">{selected.description}</p>{/if}
			{/if}
			{#if canEdit || selected === 'new'}
				<ResourceForm resource={nodeResource} object={selected === 'new' ? null : (selected as unknown as Row)} domains={data.domains} people={[]} refs={parents} fixed={{ framework: fw.id }} canChange={true} onsaved={async () => { selected = null; await invalidateAll(); }} />
				{#if selected !== 'new'}<button class="danger" onclick={() => removeNode(selected as Node)}>Delete requirement</button>{/if}
			{/if}
			<p><button class="secondary" onclick={() => (selected = null)}>Close</button></p>
		</section>
	{/key}
{/if}

<style>
	.scroll { max-height: 60vh; overflow: auto; margin-top: 10px; }
	ul.tree ul { margin-left: 4px; padding-left: 16px; border-left: 1px solid var(--line); }
	.twisty { display: inline-block; width: 22px; background: none; border: 0; color: var(--muted); padding: 0; text-align: center; cursor: pointer; }
	.rowbtn { background: none; border: 0; color: var(--text); padding: 3px 6px; text-align: left; border-radius: 4px; cursor: pointer; }
	.rowbtn:hover { background: var(--bg); }
</style>
