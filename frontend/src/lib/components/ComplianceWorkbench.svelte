<script lang="ts">
	import { untrack } from 'svelte';
	import { ApiError, createApi } from '#lib/api/client.ts';
	import MultiSelect, { type Option } from './MultiSelect.svelte';

	export type Answer = {
		id: string; result: string; status: string; observation: string;
		applied_controls: string[]; evidence: string[];
	};
	export type WorkRow = {
		id: string; ref_id: string; name: string; description: string; parent: string | null;
		assessable: boolean; weight: number; assessment: Answer | null;
	};
	type Hint = { ref_id: string; name: string; result: string };
	type Related = { id: string; source: string; target: string; source_ref: string; source_name: string; source_framework: string; target_ref: string; target_name: string; target_framework: string };

	let {
		assessmentId,
		initialRows,
		controls,
		evidence,
		others,
		canChange
	}: {
		assessmentId: string;
		initialRows: WorkRow[];
		controls: Option[];
		evidence: Option[];
		others: { id: string; name: string }[];
		canChange: boolean;
	} = $props();

	const results = [
		{ value: 'not_assessed', label: 'Not assessed', colour: '' },
		{ value: 'compliant', label: 'Compliant', colour: '#2e7d5b' },
		{ value: 'partially_compliant', label: 'Partially compliant', colour: '#c99a12' },
		{ value: 'non_compliant', label: 'Non-compliant', colour: '#b3261e' },
		{ value: 'not_applicable', label: 'Not applicable', colour: '#6b7686' }
	];
	const resultOf = (value: string | undefined) => results.find((r) => r.value === value) ?? results[0];
	const statuses = [['to_do', 'To do'], ['in_progress', 'In progress'], ['in_review', 'In review'], ['done', 'Done']];

	// The page re-creates this component per assessment ({#key}), so reading the prop once is intended.
	// svelte-ignore state_referenced_locally
	let rows = $state<WorkRow[]>(initialRows);
	let open = $state<Record<string, boolean>>({});
	let selectedId = $state<string | null>(null);
	let search = $state('');
	let resultFilter = $state('');
	let draft = $state({ result: 'not_assessed', status: 'to_do', observation: '', applied_controls: [] as string[], evidence: [] as string[] });
	let message = $state('');
	let saved = $state(false);
	let busy = $state(false);
	let related = $state<Related[]>([]);
	let hintSource = $state('');
	let hints = $state<Record<string, Hint[]>>({});
	let hintMessage = $state('');

	const children = $derived.by(() => {
		const map = new Map<string | null, WorkRow[]>();
		for (const row of rows) map.set(row.parent, [...(map.get(row.parent) ?? []), row]);
		return map;
	});
	const progress = $derived.by(() => {
		const stats = new Map<string, { done: number; total: number }>();
		const byId = new Map(rows.map((r) => [r.id, r]));
		for (const row of [...rows].reverse()) {
			const own = stats.get(row.id) ?? { done: 0, total: 0 };
			if (row.assessable) {
				own.total += 1;
				if (row.assessment && row.assessment.result !== 'not_assessed') own.done += 1;
			}
			stats.set(row.id, own);
			if (row.parent && byId.has(row.parent)) {
				const up = stats.get(row.parent) ?? { done: 0, total: 0 };
				up.done += own.done;
				up.total += own.total;
				stats.set(row.parent, up);
			}
		}
		return stats;
	});
	const summary = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const r of rows) if (r.assessable) counts[r.assessment?.result ?? 'not_assessed'] = (counts[r.assessment?.result ?? 'not_assessed'] ?? 0) + 1;
		const total = Object.values(counts).reduce((a, b) => a + b, 0);
		const applicable = total - (counts.not_applicable ?? 0);
		const assessed = applicable - (counts.not_assessed ?? 0);
		return {
			counts, total, applicable,
			assessed: applicable ? Math.round((100 * assessed) / applicable) : 0,
			compliant: applicable ? Math.round((100 * (counts.compliant ?? 0)) / applicable) : 0
		};
	});
	const filtering = $derived(search.trim() !== '' || resultFilter !== '');
	const matches = $derived(
		filtering
			? rows.filter(
					(r) =>
						r.assessable &&
						(resultFilter === '' || (r.assessment?.result ?? 'not_assessed') === resultFilter) &&
						(search.trim() === '' || `${r.ref_id} ${r.name}`.toLowerCase().includes(search.trim().toLowerCase()))
				)
			: []
	);
	const selected = $derived(rows.find((r) => r.id === selectedId) ?? null);

	// Reset the answer panel when a different requirement is chosen. Only the choice is tracked:
	// saving changes the row itself, and that must not wipe the confirmation message.
	$effect(() => {
		const id = selectedId;
		return untrack(() => {
			const row = rows.find((r) => r.id === id) ?? null;
			message = '';
			saved = false;
			related = [];
			if (!row) return;
			const a = row.assessment;
			draft = {
				result: a?.result ?? 'not_assessed', status: a?.status ?? 'to_do', observation: a?.observation ?? '',
				applied_controls: [...(a?.applied_controls ?? [])], evidence: [...(a?.evidence ?? [])]
			};
			let current = true;
			createApi().get<Related[]>(`/api/requirement-nodes/${row.id}/mappings/`).then((list) => {
				if (current) related = list;
			}).catch(() => {});
			return () => (current = false);
		});
	});

	async function save() {
		if (!selected?.assessment) return;
		busy = true;
		message = '';
		try {
			const updated = await createApi().patch<Answer>(`/api/requirement-assessments/${selected.assessment.id}/`, draft);
			selected.assessment = { ...selected.assessment, ...updated, applied_controls: draft.applied_controls, evidence: draft.evidence };
			saved = true;
			message = 'Saved.';
		} catch (error) {
			saved = false;
			message = error instanceof ApiError ? Object.values(error.fields).join(' ') || error.message : 'Saving failed.';
		} finally {
			busy = false;
		}
	}

	async function loadHints() {
		hintMessage = '';
		hints = {};
		if (!hintSource) return;
		try {
			const list = await createApi().get<{ requirement: string; from: Hint[] }[]>(`/api/compliance-assessments/${assessmentId}/suggestions/?source=${hintSource}`);
			hints = Object.fromEntries(list.map((h) => [h.requirement, h.from]));
			hintMessage = `${list.length} requirement(s) have hints.`;
		} catch (error) {
			hintMessage = error instanceof ApiError ? error.message : 'Could not load hints.';
		}
	}

	function pick(row: WorkRow) {
		selectedId = row.id;
	}
</script>

{#snippet chip(value: string | undefined)}
	{@const r = resultOf(value)}
	<span class="chip" style={r.colour ? `border-color: ${r.colour}` : ''}><span class="dot" style="background: {r.colour || 'transparent'}; border: 1px solid {r.colour || 'var(--muted)'}"></span>{r.label}</span>
{/snippet}

{#snippet line(row: WorkRow)}
	<button class="rowbtn" class:active={row.id === selectedId} onclick={() => pick(row)}>
		<span class="mono">{row.ref_id}</span> {row.name}
		{#if hints[row.id]}<span class="chip" title="Hints from the other assessment">hint</span>{/if}
	</button>
	{#if row.assessable}{@render chip(row.assessment?.result)}{/if}
{/snippet}

{#snippet branch(parent: string | null)}
	<ul class="tree">
		{#each children.get(parent) ?? [] as row (row.id)}
			{@const kids = children.get(row.id)}
			<li>
				{#if kids?.length}
					<button class="twisty" aria-expanded={!!open[row.id]} aria-label="{open[row.id] ? 'Collapse' : 'Expand'} {row.ref_id}" onclick={() => (open[row.id] = !open[row.id])}>{open[row.id] ? '▾' : '▸'}</button>
					<button class="rowbtn group" class:active={row.id === selectedId} onclick={() => { open[row.id] = !open[row.id]; pick(row); }}>
						<span class="mono">{row.ref_id}</span> {row.name}
					</button>
					<span class="muted">{progress.get(row.id)?.done ?? 0}/{progress.get(row.id)?.total ?? 0}</span>
					{#if open[row.id]}{@render branch(row.id)}{/if}
				{:else}
					<span class="twisty"></span>{@render line(row)}
				{/if}
			</li>
		{/each}
	</ul>
{/snippet}

<section class="card">
	<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px">
		<div><div class="stat">{summary.assessed}%</div><div class="muted">assessed</div><progress max="100" value={summary.assessed} aria-label="Assessed"></progress></div>
		<div><div class="stat">{summary.compliant}%</div><div class="muted">compliant of applicable</div><progress max="100" value={summary.compliant} aria-label="Compliant"></progress></div>
		{#each results.slice(1) as r (r.value)}
			<div><div class="stat">{summary.counts[r.value] ?? 0}</div><div class="muted">{r.label.toLowerCase()}</div></div>
		{/each}
	</div>
</section>

<div class="split">
	<section class="card" aria-label="Requirements">
		<div class="row">
			<div><label for="wb-search">Find</label><input id="wb-search" type="search" bind:value={search} placeholder="Reference or title" /></div>
			<div>
				<label for="wb-result">Result</label>
				<select id="wb-result" bind:value={resultFilter}>
					<option value="">Any</option>
					{#each results as r (r.value)}<option value={r.value}>{r.label}</option>{/each}
				</select>
			</div>
		</div>
		{#if others.length}
			<div class="row" style="margin-top: 8px">
				<div>
					<label for="wb-hints">Hints from another assessment</label>
					<select id="wb-hints" bind:value={hintSource} onchange={loadHints}>
						<option value="">None</option>
						{#each others as o (o.id)}<option value={o.id}>{o.name}</option>{/each}
					</select>
				</div>
			</div>
			{#if hintMessage}<p class="muted" role="status">{hintMessage}</p>{/if}
		{/if}
		<div class="scroll">
			{#if filtering}
				<p class="muted">{matches.length} match{matches.length === 1 ? '' : 'es'}</p>
				<ul class="tree">
					{#each matches.slice(0, 300) as row (row.id)}<li>{@render line(row)}</li>{/each}
				</ul>
				{#if matches.length > 300}<p class="muted">Showing the first 300. Narrow the search to see more.</p>{/if}
			{:else}
				{@render branch(null)}
			{/if}
		</div>
	</section>

	<section class="card sticky" aria-label="Requirement" aria-live="polite">
		{#if !selected}
			<p class="muted">Choose a requirement to read it and record your assessment.</p>
		{:else}
			<h2><span class="mono">{selected.ref_id}</span> {selected.name}</h2>
			{#if selected.description}<p style="white-space: pre-wrap">{selected.description}</p>{/if}

			{#if selected.assessable && selected.assessment}
				<fieldset disabled={!canChange} style="border: 0; padding: 0; margin: 0">
					<legend style="font-weight: 600">Result</legend>
					<div class="results">
						{#each results as r (r.value)}
							<label class="choice" class:on={draft.result === r.value} style={r.colour && draft.result === r.value ? `border-color: ${r.colour}` : ''}>
								<input type="radio" name="result" value={r.value} bind:group={draft.result} /> {r.label}
							</label>
						{/each}
					</div>
					<label for="wb-status">Status</label>
					<select id="wb-status" bind:value={draft.status}>{#each statuses as [v, l] (v)}<option value={v}>{l}</option>{/each}</select>
					<label for="wb-observation">Observation</label>
					<textarea id="wb-observation" rows="4" bind:value={draft.observation}></textarea>
					<MultiSelect label="Applied controls" options={controls} bind:selected={draft.applied_controls} disabled={!canChange} />
					<MultiSelect label="Evidence" options={evidence} bind:selected={draft.evidence} disabled={!canChange} />
				</fieldset>
				<p class={saved ? 'ok' : 'error'} role="status">{message}</p>
				{#if canChange}<button onclick={save} disabled={busy}>Save answer</button>{:else}<p class="muted">You can view this assessment but not change it.</p>{/if}
			{:else}
				<p class="muted">This entry groups other requirements and is not assessed itself.</p>
			{/if}

			{#if hints[selected.id]}
				<h3>Hints from the other assessment</h3>
				<ul>{#each hints[selected.id] as h (h.ref_id)}<li><span class="mono">{h.ref_id}</span> {h.name}: {resultOf(h.result).label}</li>{/each}</ul>
				<p class="muted">These requirements map onto this one. A mapping is a pointer, so check it before you copy a result.</p>
			{/if}

			{#if related.length}
				<h3>Related requirements in other frameworks</h3>
				<ul>
					{#each related as link (link.id)}
						{@const mine = link.source === selected.id}
						<li><span class="mono">{mine ? link.target_ref : link.source_ref}</span> {mine ? link.target_name : link.source_name} <span class="muted">({mine ? link.target_framework : link.source_framework})</span></li>
					{/each}
				</ul>
			{/if}
		{/if}
	</section>
</div>

<style>
	.split { display: grid; gap: 16px; grid-template-columns: minmax(280px, 5fr) minmax(300px, 6fr); align-items: start; margin-top: 16px; }
	.split > .card { margin-top: 0; }
	@media (max-width: 900px) { .split { grid-template-columns: 1fr; } }
	.scroll { max-height: 68vh; overflow: auto; margin-top: 10px; }
	.sticky { position: sticky; top: 8px; }
	ul.tree ul { margin-left: 4px; padding-left: 16px; border-left: 1px solid var(--line); }
	li { display: block; }
	.twisty { display: inline-block; width: 22px; background: none; border: 0; color: var(--muted); padding: 0; text-align: center; cursor: pointer; }
	.rowbtn { background: none; border: 0; color: var(--text); padding: 3px 6px; text-align: left; border-radius: 4px; cursor: pointer; }
	.rowbtn:hover { background: var(--bg); }
	.rowbtn.active { background: var(--bg); outline: 2px solid var(--accent); }
	.group { font-weight: 600; }
	.results { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
	.choice { display: inline-flex; gap: 6px; align-items: center; font-weight: 400; border: 1px solid var(--line); border-radius: 6px; padding: 4px 10px; margin: 0; cursor: pointer; }
	.choice.on { border-width: 2px; padding: 3px 9px; font-weight: 600; }
	.choice input { width: auto; }
</style>
