<script lang="ts">
	import History from '#lib/components/History.svelte';
	let { data } = $props();

	const actions = ['create', 'update', 'delete', 'login', 'logout', 'login_failed', 'access'];
	const link = (page: number) => {
		const q = new URLSearchParams();
		if (data.filters.object_type) q.set('object_type', data.filters.object_type);
		if (data.filters.action) q.set('action', data.filters.action);
		q.set('page', String(page));
		return `?${q}`;
	};
</script>

<svelte:head><title>Audit log</title></svelte:head>

<h1 style="margin-top: 20px">Audit log</h1>
<p class="muted">Every change, sign-in and file download, in order. Records are append-only and chained, so edits or removals show up when the chain is checked.</p>

<form class="card row" method="get">
	<div>
		<label for="object_type">Object type</label>
		<select id="object_type" name="object_type">
			<option value="">All</option>
			{#each data.objectTypes as type (type.key)}<option value={type.key} selected={type.key === data.filters.object_type}>{type.label}</option>{/each}
		</select>
	</div>
	<div>
		<label for="action">Action</label>
		<select id="action" name="action">
			<option value="">All</option>
			{#each actions as action (action)}<option selected={action === data.filters.action}>{action}</option>{/each}
		</select>
	</div>
	<button type="submit">Filter</button>
</form>

<section class="card">
	<p class="muted">{data.events.count} matching records</p>
	<History events={data.events.results} />
	<p>
		{#if data.events.previous}<a href={link(data.page - 1)}>Newer</a>{/if}
		{#if data.events.next}<a href={link(data.page + 1)} style="margin-left: 16px">Older</a>{/if}
	</p>
</section>
