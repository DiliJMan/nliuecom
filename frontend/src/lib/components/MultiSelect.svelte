<script lang="ts">
	export type Option = { id: string; label: string };

	let {
		label,
		options,
		selected = $bindable(),
		disabled = false,
		error = ''
	}: { label: string; options: Option[]; selected: string[]; disabled?: boolean; error?: string } = $props();

	let filter = $state('');
	const shown = $derived(options.filter((o) => o.label.toLowerCase().includes(filter.toLowerCase())));
	const missing = $derived(selected.filter((id) => !options.some((o) => o.id === id)));

	function toggle(id: string, on: boolean) {
		selected = on ? [...selected, id] : selected.filter((s) => s !== id);
	}
</script>

<fieldset style="border: 0; padding: 0; margin: 10px 0 0">
	<legend style="font-weight: 600">{label} <span class="muted">({selected.length} selected)</span></legend>
	{#if options.length > 8}
		<input type="search" placeholder="Filter…" aria-label="Filter {label}" bind:value={filter} style="margin-bottom: 6px" />
	{/if}
	<div class="pick">
		{#each shown as option (option.id)}
			<label style="font-weight: 400; margin: 2px 0">
				<input type="checkbox" {disabled} checked={selected.includes(option.id)} onchange={(e) => toggle(option.id, e.currentTarget.checked)} />
				{option.label}
			</label>
		{:else}
			<span class="muted">Nothing to choose from.</span>
		{/each}
		{#if missing.length}<span class="muted">{missing.length} linked item(s) are not visible to you.</span>{/if}
	</div>
	{#if error}<span class="error">{error}</span>{/if}
</fieldset>

<style>
	.pick { max-height: 180px; overflow: auto; border: 1px solid var(--line); border-radius: var(--radius); padding: 6px 10px; background: var(--bg); }
</style>
