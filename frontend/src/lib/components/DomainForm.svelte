<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { ApiError, createApi, type Schemas } from '#lib/api/client.ts';

	let {
		domain,
		fields,
		canChange,
		canDelete
	}: {
		domain: Schemas['Domain'];
		fields: Schemas['CustomFieldDefinition'][];
		canChange: boolean;
		canDelete: boolean;
	} = $props();

	const kinds = [
		['organisation', 'Organisation'],
		['subsidiary', 'Subsidiary'],
		['business_unit', 'Business unit'],
		['entity', 'Entity'],
		['team', 'Team'],
		['other', 'Other']
	] as const;

	// The form is re-created per domain ({#key} in the page), so reading the initial props once is intended.
	// svelte-ignore state_referenced_locally
	const initial: Record<string, unknown> = { ...domain.custom_fields };
	// svelte-ignore state_referenced_locally
	let name = $state(domain.name);
	// svelte-ignore state_referenced_locally
	let description = $state(domain.description ?? '');
	// svelte-ignore state_referenced_locally
	let kind = $state<string>(domain.kind ?? 'other');
	let values = $state<Record<string, unknown>>({ ...initial });
	let message = $state('');
	let problems = $state<Record<string, string>>({});
	let busy = $state(false);

	function toggle(key: string, choice: string, on: boolean) {
		const current = Array.isArray(values[key]) ? (values[key] as string[]) : [];
		values[key] = on ? [...current, choice] : current.filter((c) => c !== choice);
	}

	async function save(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		message = '';
		problems = {};
		const custom = Object.fromEntries(
			Object.entries(values).filter(([, v]) => v !== '' && v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0))
		);
		try {
			await createApi().patch(`/api/domains/${domain.id}/`, { name, description, kind, custom_fields: custom });
			await invalidateAll();
			message = 'Saved.';
		} catch (error) {
			if (error instanceof ApiError) {
				problems = error.fields;
				message = error.status === 400 ? 'Please correct the highlighted fields.' : error.message;
			} else message = 'Saving failed.';
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (!confirm(`Delete "${domain.name}"? This is recorded in the audit log.`)) return;
		try {
			await createApi().delete(`/api/domains/${domain.id}/`);
			await goto('/');
			await invalidateAll();
		} catch (error) {
			message = error instanceof ApiError ? error.message : 'Deleting failed.';
		}
	}

	const customErrors = (): Record<string, string> => {
		try { return JSON.parse(problems.custom_fields ?? '{}'); } catch { return {}; }
	};
</script>

<form class="card" onsubmit={save}>
	<h2>Details</h2>
	<fieldset disabled={!canChange} style="border: 0; padding: 0; margin: 0">
		<label for="name">Name</label>
		<input id="name" required maxlength="200" bind:value={name} />
		{#if problems.name}<span class="error">{problems.name}</span>{/if}
		<label for="kind">Type</label>
		<select id="kind" bind:value={kind}>
			{#each kinds as [value, label] (value)}<option {value}>{label}</option>{/each}
		</select>
		<label for="description">Description</label>
		<textarea id="description" rows="3" bind:value={description}></textarea>

		{#each fields as field (field.id)}
			{@const id = `cf-${field.key}`}
			{#if field.field_type === 'boolean'}
				<label for={id}><input {id} type="checkbox" checked={values[field.key] === true} onchange={(e) => (values[field.key] = e.currentTarget.checked)} /> {field.label}</label>
			{:else if field.field_type === 'multi_choice'}
				<fieldset style="border: 0; padding: 0; margin: 10px 0 0">
					<legend style="font-weight: 600">{field.label}</legend>
					{#each field.choices as choice (choice)}
						<label style="font-weight: 400; display: inline-block; margin-right: 12px">
							<input type="checkbox" checked={Array.isArray(values[field.key]) && (values[field.key] as string[]).includes(choice)} onchange={(e) => toggle(field.key, choice, e.currentTarget.checked)} /> {choice}
						</label>
					{/each}
				</fieldset>
			{:else}
				<label for={id}>{field.label}{field.required ? ' *' : ''}</label>
				{#if field.field_type === 'choice'}
					<select {id} bind:value={values[field.key]}>
						<option value="">(none)</option>
						{#each field.choices as choice (choice)}<option>{choice}</option>{/each}
					</select>
				{:else if field.field_type === 'number'}
					<input {id} type="number" step="any" value={values[field.key] ?? ''} oninput={(e) => (values[field.key] = e.currentTarget.value === '' ? '' : Number(e.currentTarget.value))} />
				{:else}
					<input {id} type={field.field_type === 'date' ? 'date' : 'text'} bind:value={values[field.key]} />
				{/if}
			{/if}
			{#if field.help_text}<div class="muted">{field.help_text}</div>{/if}
			{#if customErrors()[field.key]}<span class="error">{customErrors()[field.key]}</span>{/if}
		{/each}
	</fieldset>
	<p class={problems.name || Object.keys(problems).length ? 'error' : 'ok'} role="status" aria-live="polite">{message}</p>
	{#if canChange}<button type="submit" disabled={busy}>Save changes</button>{/if}
	{#if canDelete}<button type="button" class="danger" onclick={remove}>Delete domain</button>{/if}
	{#if !canChange}<p class="muted">You can view this domain but not change it.</p>{/if}
</form>
