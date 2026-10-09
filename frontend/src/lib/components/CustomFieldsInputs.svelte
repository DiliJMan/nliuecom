<script lang="ts">
	import type { Schemas } from '#lib/api/client.ts';

	let {
		definitions,
		values = $bindable(),
		errors = {},
		disabled = false
	}: {
		definitions: Schemas['CustomFieldDefinition'][];
		values: Record<string, unknown>;
		errors?: Record<string, string>;
		disabled?: boolean;
	} = $props();

	function toggle(key: string, choice: string, on: boolean) {
		const current = Array.isArray(values[key]) ? (values[key] as string[]) : [];
		values[key] = on ? [...current, choice] : current.filter((c) => c !== choice);
	}
</script>

{#each definitions as field (field.id)}
	{@const id = `cf-${field.key}`}
	{#if field.field_type === 'boolean'}
		<label for={id}>
			<input {id} type="checkbox" {disabled} checked={values[field.key] === true} onchange={(e) => (values[field.key] = e.currentTarget.checked)} />
			{field.label}
		</label>
	{:else if field.field_type === 'multi_choice'}
		<fieldset style="border: 0; padding: 0; margin: 10px 0 0">
			<legend style="font-weight: 600">{field.label}</legend>
			{#each field.choices ?? [] as choice (choice)}
				<label style="font-weight: 400; display: inline-block; margin-right: 12px">
					<input type="checkbox" {disabled} checked={Array.isArray(values[field.key]) && (values[field.key] as string[]).includes(choice)} onchange={(e) => toggle(field.key, choice, e.currentTarget.checked)} />
					{choice}
				</label>
			{/each}
		</fieldset>
	{:else}
		<label for={id}>{field.label}{field.required ? ' *' : ''}</label>
		{#if field.field_type === 'choice'}
			<select {id} {disabled} bind:value={values[field.key]}>
				<option value="">(none)</option>
				{#each field.choices ?? [] as choice (choice)}<option>{choice}</option>{/each}
			</select>
		{:else if field.field_type === 'number'}
			<input {id} {disabled} type="number" step="any" value={values[field.key] ?? ''} oninput={(e) => (values[field.key] = e.currentTarget.value === '' ? '' : Number(e.currentTarget.value))} />
		{:else}
			<input {id} {disabled} type={field.field_type === 'date' ? 'date' : 'text'} bind:value={values[field.key]} />
		{/if}
	{/if}
	{#if field.help_text}<div class="muted">{field.help_text}</div>{/if}
	{#if errors[field.key]}<span class="error">{errors[field.key]}</span>{/if}
{/each}
