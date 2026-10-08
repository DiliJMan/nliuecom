<script lang="ts">
	import DomainTree from '#lib/components/DomainTree.svelte';
	let { data } = $props();
</script>

<svelte:head><title>Domains</title></svelte:head>

<h1 style="margin-top: 20px">Domains</h1>
<p class="muted">Your organisation, split into the units that own risks, assets and controls.</p>
<section class="card">
	{#if data.tree.length}
		<DomainTree nodes={data.tree} />
	{:else}
		<p class="muted">No domains are visible to you yet. Ask an administrator to assign you a role.</p>
	{/if}
</section>
