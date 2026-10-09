<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import History from '#lib/components/History.svelte';
	import ResourceForm from '#lib/components/ResourceForm.svelte';
	import { resources } from '#lib/resources.ts';

	let { data } = $props();
	const resource = $derived(resources[data.key]);
	const can = (action: string) => data.permissions.includes(`${resource.objectType}:${action}`);
	const title = $derived(String(data.object[resource.nameKey] ?? resource.label));
</script>

<svelte:head><title>{title}</title></svelte:head>

<p class="muted" style="margin-top: 20px"><a href="/r/{resource.key}">{resource.plural}</a></p>
<h1>{title}</h1>

{#key data.object.id}
	<section class="card">
		<ResourceForm
			{resource}
			object={data.object}
			domains={data.domains}
			people={data.people}
			refs={data.refs}
			canChange={can('change')}
			canDelete={can('delete')}
			onsaved={() => invalidateAll()}
			ondeleted={() => goto(`/r/${resource.key}`)}
		/>
	</section>
{/key}

<section class="card">
	<h2>History</h2>
	<History events={data.trail} />
</section>
