<script lang="ts">
	import { ApiError, createApi, type Schemas } from '#lib/api/client.ts';
	import type { Field, Resource, Row } from '#lib/resources.ts';
	import CustomFieldsInputs from './CustomFieldsInputs.svelte';
	import MultiSelect, { type Option } from './MultiSelect.svelte';

	type Person = { id: string; email: string; name: string };

	let {
		resource,
		fields = resource.fields,
		object = null,
		domains,
		people,
		refs,
		fixed = {},
		customFieldType = resource.objectType,
		canChange = true,
		canDelete = false,
		submitLabel = '',
		onsaved,
		ondeleted
	}: {
		resource: Resource;
		fields?: Field[];
		object?: Row | null;
		domains: Schemas['Domain'][];
		people: Person[];
		refs: Record<string, Option[]>;
		/** Values forced by the page (for example the parent assessment) and never shown. */
		fixed?: Record<string, unknown>;
		customFieldType?: string;
		canChange?: boolean;
		canDelete?: boolean;
		submitLabel?: string;
		onsaved?: (saved: Row) => void | Promise<void>;
		ondeleted?: () => void | Promise<void>;
	} = $props();

	// svelte-ignore state_referenced_locally
	const editing = object !== null;
	// A dropdown shows its first option, so a new form must start from that option's value.
	const blank = (f: Field): unknown =>
		f.default !== undefined ? f.default
			: f.kind === 'multi' ? [] : f.kind === 'bool' ? false
			: f.kind === 'select' ? (f.options?.[0]?.value ?? '')
			: f.kind === 'number' || f.kind === 'intselect' ? null : '';

	// The page re-creates this form for each object ({#key}), so reading props once is intended.
	// svelte-ignore state_referenced_locally
	let values = $state<Record<string, any>>(
		Object.fromEntries(
			fields.map((f) => [
				f.key,
				object ? (object[f.key] ?? blank(f)) : f.kind === 'domain' && domains.length === 1 ? domains[0].id : blank(f)
			])
		)
	);
	// svelte-ignore state_referenced_locally
	let customValues = $state<Record<string, unknown>>({ ...(object?.custom_fields ?? {}) });
	let definitions = $state<Schemas['CustomFieldDefinition'][]>([]);
	let uploaded = $state<Option[]>([]);
	let problems = $state<Record<string, string>>({});
	let customProblems = $state<Record<string, string>>({});
	let message = $state('');
	let saved = $state(false);
	let busy = $state(false);
	let uploading = $state(false);

	const domainId = $derived<string>((values.domain as string) || (fixed.domain as string) || (object?.domain as string) || '');

	$effect(() => {
		const id = domainId;
		if (!resource.supportsCustomFields || !id) {
			definitions = [];
			return;
		}
		let current = true;
		createApi()
			.get<{ results: Schemas['CustomFieldDefinition'][] }>(`/api/custom-fields/?object_type=${customFieldType}&domain=${id}&page_size=100`)
			.then((page) => {
				if (current) definitions = page.results;
			})
			.catch(() => {
				if (current) definitions = [];
			});
		return () => (current = false);
	});

	const isLocked = (f: Field) => editing && f.fixedOnEdit;

	function payload(): Record<string, unknown> {
		const body: Record<string, unknown> = editing ? {} : { ...fixed };
		for (const f of fields) {
			if (isLocked(f)) continue;
			let v = values[f.key];
			if (f.kind === 'number' || f.kind === 'intselect') v = v === '' || v === null || v === undefined ? null : Number(v);
			else if (f.kind === 'date' || f.kind === 'user' || f.kind === 'ref' || f.kind === 'attachment') v = v === '' ? null : v;
			if (f.kind === 'ref' && v === null && f.required) continue;
			body[f.key] = v;
		}
		if (resource.supportsCustomFields) {
			body.custom_fields = Object.fromEntries(
				Object.entries(customValues).filter(([, v]) => v !== '' && v !== null && v !== undefined && !(Array.isArray(v) && v.length === 0))
			);
		}
		return body;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		message = '';
		saved = false;
		problems = {};
		customProblems = {};
		try {
			const api = createApi();
			const body = payload();
			const result = editing
				? await api.patch<Row>(`${resource.path}${object!.id}/`, body)
				: await api.post<Row>(resource.path, body);
			saved = true;
			message = editing ? 'Saved.' : `${resource.label} created.`;
			await onsaved?.(result);
		} catch (error) {
			if (error instanceof ApiError) {
				problems = error.fields;
				try {
					customProblems = JSON.parse(problems.custom_fields ?? '{}');
				} catch {
					customProblems = {};
				}
				message = error.status === 400 ? 'Please correct the highlighted fields.' : error.message;
			} else message = 'Saving failed.';
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (!confirm(`Delete this ${resource.label.toLowerCase()}? The deletion is recorded in the audit log.`)) return;
		try {
			await createApi().delete(`${resource.path}${object!.id}/`);
			await ondeleted?.();
		} catch (error) {
			saved = false;
			message = error instanceof ApiError ? error.message : 'Deleting failed.';
		}
	}

	async function upload(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		if (!domainId) {
			message = 'Choose the domain before uploading a file.';
			input.value = '';
			return;
		}
		uploading = true;
		message = '';
		try {
			const form = new FormData();
			form.append('domain', domainId);
			form.append('file', file);
			const stored = await createApi().post<Schemas['Attachment']>('/api/attachments/', form);
			uploaded = [...uploaded, { id: stored.id, label: stored.original_name ?? file.name }];
			values.attachment = stored.id;
		} catch (error) {
			problems = { ...problems, attachment: error instanceof ApiError ? Object.values(error.fields).join(' ') || error.message : 'Upload failed.' };
		} finally {
			uploading = false;
			input.value = '';
		}
	}

	const fieldId = (f: Field) => `f-${resource.key}-${f.key}`;
	const personLabel = (p: Person) => (p.name && p.name !== p.email ? `${p.name} (${p.email})` : p.email);
</script>

<form onsubmit={submit}>
	<fieldset disabled={!canChange} style="border: 0; padding: 0; margin: 0">
		{#each fields as f (f.key)}
			{@const id = fieldId(f)}
			{#if f.kind === 'bool'}
				<label for={id}><input {id} type="checkbox" bind:checked={values[f.key]} /> {f.label}</label>
			{:else if f.kind === 'multi'}
				<MultiSelect label={f.label} options={refs[f.ref ?? ''] ?? []} bind:selected={values[f.key]} disabled={!canChange} error={problems[f.key]} />
				{#if f.help}<div class="muted">{f.help}</div>{/if}
			{:else}
				<label for={id}>{f.label}{f.required ? ' *' : ''}</label>
				{#if f.kind === 'textarea'}
					<textarea {id} rows="3" bind:value={values[f.key]}></textarea>
				{:else if f.kind === 'select' || f.kind === 'intselect'}
					<select {id} bind:value={values[f.key]}>
						{#if f.kind === 'intselect' && !f.options?.some((o) => o.value === '')}<option value={null}>(not set)</option>{/if}
						{#each f.options ?? [] as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
					</select>
				{:else if f.kind === 'domain'}
					<select {id} required={f.required} disabled={isLocked(f) || !canChange} bind:value={values[f.key]}>
						<option value="" disabled>Choose…</option>
						{#each domains as d (d.id)}<option value={d.id}>{' '.repeat((d.depth ?? 0) * 3)}{d.name}</option>{/each}
					</select>
				{:else if f.kind === 'user'}
					<select {id} bind:value={values[f.key]}>
						<option value="">(nobody)</option>
						{#each people as p (p.id)}<option value={p.id}>{personLabel(p)}</option>{/each}
					</select>
				{:else if f.kind === 'ref'}
					<select {id} required={f.required} disabled={isLocked(f) || !canChange} bind:value={values[f.key]}>
						<option value="" disabled={f.required}>{f.required ? 'Choose…' : '(none)'}</option>
						{#each refs[f.ref ?? ''] ?? [] as o (o.id)}<option value={o.id}>{o.label}</option>{/each}
					</select>
				{:else if f.kind === 'attachment'}
					<select {id} bind:value={values[f.key]}>
						<option value="">(no file)</option>
						{#each [...(refs[f.ref ?? 'attachments'] ?? []), ...uploaded] as o (o.id)}<option value={o.id}>{o.label}</option>{/each}
					</select>
					<input type="file" aria-label="Upload a new file" disabled={uploading || !canChange} onchange={upload} style="margin-top: 6px" />
					{#if uploading}<span class="muted">Uploading…</span>{/if}
				{:else}
					<input
						{id}
						type={f.kind === 'number' ? 'number' : f.kind === 'date' ? 'date' : 'text'}
						required={f.required}
						bind:value={values[f.key]}
					/>
				{/if}
				{#if f.help}<div class="muted">{f.help}</div>{/if}
				{#if problems[f.key]}<span class="error">{problems[f.key]}</span>{/if}
			{/if}
		{/each}
		{#if resource.supportsCustomFields && definitions.length}
			<CustomFieldsInputs {definitions} bind:values={customValues} errors={customProblems} disabled={!canChange} />
		{/if}
	</fieldset>
	<p class={saved ? 'ok' : 'error'} role="status" aria-live="polite">{message}</p>
	{#if canChange}<button type="submit" disabled={busy}>{submitLabel || (editing ? 'Save changes' : `Create ${resource.label.toLowerCase()}`)}</button>{/if}
	{#if editing && canDelete}<button type="button" class="danger" onclick={remove}>Delete</button>{/if}
	{#if editing && !canChange}<p class="muted">You can view this {resource.label.toLowerCase()} but not change it.</p>{/if}
</form>
