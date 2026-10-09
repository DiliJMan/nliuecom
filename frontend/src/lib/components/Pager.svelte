<script lang="ts">
	let { page, count, pageSize = 50, href }: { page: number; count: number; pageSize?: number; href: (page: number) => string } = $props();
	const last = $derived(Math.max(1, Math.ceil(count / pageSize)));
</script>

{#if last > 1}
	<nav aria-label="Pages" style="display: flex; gap: 16px; margin-top: 12px; align-items: center">
		{#if page > 1}<a href={href(page - 1)}>Previous</a>{/if}
		<span class="muted">Page {page} of {last}</span>
		{#if page < last}<a href={href(page + 1)}>Next</a>{/if}
	</nav>
{/if}
