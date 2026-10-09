<script lang="ts">
	let { data } = $props();
	const d = $derived(data.dashboard);
	const statusLabels: Record<string, string> = {
		to_do: 'To do', planned: 'Planned', in_progress: 'In progress', active: 'Active', on_hold: 'On hold', deprecated: 'Deprecated'
	};
	const maxLevel = $derived(Math.max(1, ...(d?.risk.by_level.map((l) => l.count) ?? [1])));
</script>

<svelte:head><title>Dashboard</title></svelte:head>

<h1 style="margin-top: 20px">Dashboard</h1>

{#if !d}
	<p class="muted">The summary is not available right now.</p>
{:else}
	<div class="grid">
		<section class="card">
			<h2>My tasks</h2>
			<div class="stat">{d.tasks.open}</div>
			<p class="muted" style="margin: 4px 0 8px">open</p>
			<p style="margin: 0">
				<span class={d.tasks.overdue ? 'error' : ''}><strong>{d.tasks.overdue}</strong> overdue</span> ·
				<strong>{d.tasks.due_this_week}</strong> due this week
			</p>
			<p><a href="/r/tasks?assignee=me">See my tasks</a></p>
		</section>

		<section class="card">
			<h2>Inventory</h2>
			<p style="margin: 0"><span class="stat">{d.assets}</span> <span class="muted">assets</span></p>
			<p style="margin: 6px 0 0"><span class="stat">{d.controls.total}</span> <span class="muted">applied controls</span></p>
			<p class="muted" style="margin: 6px 0 0">
				{#each Object.entries(d.controls.by_status) as [status, count], i (status)}{i ? ' · ' : ''}{count} {(statusLabels[status] ?? status).toLowerCase()}{/each}
			</p>
		</section>

		<section class="card">
			<h2>Risk</h2>
			{#if d.risk.scenarios === 0}
				<p class="muted">No scenarios yet. <a href="/r/risk-assessments">Start a risk assessment</a>.</p>
			{:else}
				<p class="muted" style="margin-top: 0">{d.risk.scenarios} scenario{d.risk.scenarios === 1 ? '' : 's'}{d.risk.unrated ? `, ${d.risk.unrated} not rated` : ''}. Residual level where rated, otherwise current.</p>
				{#each d.risk.by_level as level (level.name)}
					<div style="display: grid; grid-template-columns: 90px 1fr 32px; gap: 8px; align-items: center; margin: 4px 0">
						<span>{level.name}</span>
						<span style="background: var(--line); border-radius: 4px; height: 12px; display: block">
							<span style="display: block; height: 12px; border-radius: 4px; background: {level.colour}; width: {(100 * level.count) / maxLevel}%"></span>
						</span>
						<strong>{level.count}</strong>
					</div>
				{/each}
			{/if}
		</section>
	</div>

	<section class="card">
		<h2>Compliance</h2>
		{#if d.compliance.length}
			<table>
				<thead><tr><th scope="col">Assessment</th><th scope="col">Framework</th><th scope="col">Domain</th><th scope="col" style="width: 28%">Progress</th></tr></thead>
				<tbody>
					{#each d.compliance as a (a.id)}
						<tr>
							<td><a href="/compliance/{a.id}">{a.name}</a></td>
							<td>{a.framework}</td>
							<td>{a.domain}</td>
							<td>
								<progress max="100" value={a.summary.assessed_percent} aria-label="Assessed {a.summary.assessed_percent}%"></progress>
								<span class="muted">{a.summary.assessed_percent}% assessed · {a.summary.compliant_percent}% compliant</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<p class="muted">No compliance assessments yet. <a href="/frameworks">Load a framework</a>, then <a href="/r/compliance-assessments">start an assessment</a>.</p>
		{/if}
	</section>
{/if}
