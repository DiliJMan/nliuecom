<script lang="ts">
	import '#lib/app.css';
	let { data, children } = $props();
</script>

{@render children()}

{#if data.about}
	<footer class="shell muted" style="padding-top: 24px; font-size: 0.85rem">
		{data.about.name} is free software under the
		<a href={data.about.licence_url} rel="noreferrer">{data.about.licence}</a> licence.
		<a href={data.about.source_url} rel="noreferrer">Source code</a>
	</footer>
{/if}
