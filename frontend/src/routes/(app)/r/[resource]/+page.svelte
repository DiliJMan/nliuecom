<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { createApi } from '#lib/api/client.ts';
	import Pager from '#lib/components/Pager.svelte';
	import ResourceForm from '#lib/components/ResourceForm.svelte';
	import { labelOf, resources, type Column, type Row } from '#lib/resources.ts';

	let { data } = $props();
	const resource = $derived(resources[data.key]);
	const domainName = $derived(new Map(data.domains.map((d) => [d.id, d.name])));
	const personName = $derived(new Map(data.people.map((p) => [p.id, p.name || p.email])));
	let creating = $state(false);
	let actionError = $state('');

	function cell(row: Row, column: Column): string {
		const value = row[column.key];
		switch (column.format) {
			case 'domain': return domainName.get(value) ?? '';
			case 'user': return value ? (personName.get(value) ?? '') : '';
			case 'enum': return labelOf(column.options, value);
			case 'percent': return value && typeof value === 'object' ? `${value.compliant_percent}%` : '';
			case 'date': return value ?? '';
			default: return value === null || value === undefined ? '' : String(value);
		}
	}
	const href = (row: Row) => resource.href?.(row) ?? `/r/${resource.key}/${row.id}`;
	const link = (patch: Record<string, string>) => {
		const q = new URLSearchParams();
		for (const [k, v] of Object.entries({ ...data.active, ...patch })) if (v) q.set(k, v);
		return `?${q}`;
	};

	async function run(action: { path: (row: Row) => string }, row: Row) {
		actionError = '';
		try {
			await createApi().post(action.path(row));
			await invalidateAll();
		} catch (error) {
			actionError = error instanceof Error ? error.message : 'The action failed.';
		}
	}
</script>

<svelte:head><title>{resource.plural}</title></svelte:head>

<h1 style="margin-top: 20px">{resource.plural}</h1>
<p class="muted">{resource.intro}</p>

<form class="card row" method="get" aria-label="Filter {resource.plural}">
	<div><label for="search">Search</label><input id="search" name="search" type="search" value={data.active.search} /></div>
	<div>
		<label for="domain">Domain</label>
		<select id="domain" name="domain">
			<option value="">All domains</option>
			{#each data.domains as d (d.id)}<option value={d.id} selected={d.id === data.active.domain}>{' '.repeat((d.depth ?? 0) * 3)}{d.name}</option>{/each}
		</select>
	</div>
	{#each resource.filters ?? [] as filter (filter.key)}
		<div>
			<label for={filter.key}>{filter.label}</label>
			<select id={filter.key} name={filter.key}>
				<option value="">All</option>
				{#each filter.options as o (o.value)}<option value={o.value} selected={String(o.value) === data.active[filter.key]}>{o.label}</option>{/each}
			</select>
		</div>
	{/each}
	<button type="submit">Apply</button>
	<button type="button" class="secondary" onclick={() => (creating = !creating)} aria-expanded={creating}>{creating ? 'Close form' : `New ${resource.label.toLowerCase()}`}</button>
</form>

{#if creating}
	<section class="card" aria-label="New {resource.label.toLowerCase()}">
		<h2>New {resource.label.toLowerCase()}</h2>
		<ResourceForm
			{resource}
			domains={data.domains}
			people={data.people}
			refs={data.refs}
			onsaved={async (row) => {
				if (resource.href) await goto(resource.href(row));
				else {
					creating = false;
					await invalidateAll();
				}
			}}
		/>
	</section>
{/if}

<section class="card">
	<p class="muted">{data.list.count} {data.list.count === 1 ? resource.label.toLowerCase() : resource.plural.toLowerCase()}</p>
	{#if actionError}<p class="error" role="alert">{actionError}</p>{/if}
	{#if data.list.results.length}
		<table>
			<thead>
				<tr>
					{#each resource.columns as column (column.key)}<th scope="col">{column.label}</th>{/each}
					{#if resource.rowActions}<th scope="col"><span class="sr-only">Actions</span></th>{/if}
				</tr>
			</thead>
			<tbody>
				{#each data.list.results as row (row.id)}
					<tr>
						{#each resource.columns as column, i (column.key)}
							<td>
								{#if i === 0}<a href={href(row)}>{cell(row, column) || 'Untitled'}</a>
									{#if row.overdue}<span class="badge" style="color: var(--danger); border-color: var(--danger)">overdue</span>{/if}
								{:else}{cell(row, column)}{/if}
							</td>
						{/each}
						{#if resource.rowActions}
							<td>
								{#each resource.rowActions as action (action.label)}
									{#if !action.show || action.show(row)}<button class="secondary" onclick={() => run(action, row)}>{action.label}</button>{/if}
								{/each}
							</td>
						{/if}
					</tr>
				{/each}
			</tbody>
		</table>
		<Pager page={data.page} count={data.list.count} href={(p) => link({ page: String(p) })} />
	{:else}
		<p class="muted">Nothing here yet.</p>
	{/if}
</section>
