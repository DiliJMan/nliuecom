<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { createApi } from '#lib/api/client.ts';
	import Heatmap from '#lib/components/Heatmap.svelte';
	import History from '#lib/components/History.svelte';
	import ResourceForm from '#lib/components/ResourceForm.svelte';
	import { resources, scenarioFields, type Resource, type Row } from '#lib/resources.ts';

	let { data } = $props();
	const can = (action: string, type = 'risk.riskassessment') => data.permissions.includes(`${type}:${action}`);
	const matrix = $derived(data.heatmap.matrix);
	const scenarioResource = $derived<Resource>({
		key: 'risk-scenarios', path: '/api/risk-scenarios/', objectType: 'risk.riskscenario', label: 'Scenario',
		plural: 'Scenarios', intro: '', nameKey: 'name', columns: [], supportsCustomFields: true,
		fields: scenarioFields(matrix)
	});
	let selected = $state<Row | 'new' | null>(null);
	const levelOf = (row: Row, which: 'current' | 'residual') => row[`${which}_level`] as { name: string; colour: string } | null;

	async function remove(row: Row) {
		if (!confirm('Delete this scenario? The deletion is recorded in the audit log.')) return;
		await createApi().delete(`/api/risk-scenarios/${row.id}/`);
		selected = null;
		await invalidateAll();
	}
</script>

<svelte:head><title>{data.assessment.name}</title></svelte:head>

<p class="muted" style="margin-top: 20px"><a href="/r/risk-assessments">Risk assessments</a></p>
<h1>{data.assessment.name}</h1>
<p class="muted">Matrix: {matrix.name} · {data.scenarios.length} scenario{data.scenarios.length === 1 ? '' : 's'}{data.heatmap.unrated ? `, ${data.heatmap.unrated} not yet rated` : ''}</p>

<div class="grid">
	<section class="card"><Heatmap {matrix} counts={data.heatmap.current} title="Current risk" /></section>
	<section class="card"><Heatmap {matrix} counts={data.heatmap.residual} title="Residual risk (after controls)" /></section>
</div>

<section class="card">
	<div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap">
		<h2 style="margin: 0">Scenarios</h2>
		{#if can('add', 'risk.riskscenario')}<button onclick={() => (selected = 'new')}>New scenario</button>{/if}
	</div>
	{#if data.scenarios.length}
		<table>
			<thead><tr><th scope="col">Reference</th><th scope="col">Scenario</th><th scope="col">Current</th><th scope="col">Residual</th><th scope="col">Treatment</th></tr></thead>
			<tbody>
				{#each data.scenarios as row (row.id)}
					<tr>
						<td>{row.ref_id}</td>
						<td><button class="secondary" style="border: 0; padding: 0; text-align: left" onclick={() => (selected = row)}>{row.name}</button></td>
						{#each ['current', 'residual'] as const as which (which)}
							{@const level = levelOf(row, which)}
							<td>{#if level}<span class="chip" style="border-color: {level.colour}"><span class="dot" style="background: {level.colour}"></span>{level.name}</span>{:else}<span class="muted">not rated</span>{/if}</td>
						{/each}
						<td>{row.treatment}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<p class="muted">No scenarios yet.</p>
	{/if}
</section>

{#if selected}
	{#key selected === 'new' ? 'new' : selected.id}
		<section class="card" aria-label="Scenario">
			<h2>{selected === 'new' ? 'New scenario' : selected.name}</h2>
			<ResourceForm
				resource={scenarioResource}
				object={selected === 'new' ? null : selected}
				domains={data.domains}
				people={data.people}
				refs={data.scenarioRefs}
				fixed={{ risk_assessment: data.assessment.id, domain: data.assessment.domain }}
				canChange={selected === 'new' ? can('add', 'risk.riskscenario') : can('change', 'risk.riskscenario')}
				canDelete={false}
				onsaved={async () => {
					selected = null;
					await invalidateAll();
				}}
			/>
			<p>
				<button class="secondary" onclick={() => (selected = null)}>Close</button>
				{#if selected !== 'new' && can('delete', 'risk.riskscenario')}<button class="danger" onclick={() => remove(selected as Row)}>Delete scenario</button>{/if}
			</p>
		</section>
	{/key}
{/if}

<details class="card">
	<summary><strong>Assessment settings</strong></summary>
	{#key data.assessment.id}
		<ResourceForm
			resource={resources['risk-assessments']}
			object={data.assessment}
			domains={data.domains}
			people={data.people}
			refs={data.assessmentRefs}
			canChange={can('change')}
			canDelete={false}
			onsaved={() => invalidateAll()}
		/>
	{/key}
</details>

<section class="card">
	<h2>History</h2>
	<History events={data.trail} />
</section>
