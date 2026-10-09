<script lang="ts" module>
	export type TreeNode = { id: string; name: string; kind: string; depth: number; children: TreeNode[] };
</script>

<script lang="ts">
	import DomainTree from './DomainTree.svelte';
	let { nodes }: { nodes: TreeNode[] } = $props();
</script>

<ul class="tree">
	{#each nodes as node (node.id)}
		<li>
			<a href="/domains/{node.id}">{node.name}</a><span class="badge">{node.kind.replace('_', ' ')}</span>
			{#if node.children.length}
				<DomainTree nodes={node.children} />
			{/if}
		</li>
	{/each}
</ul>
