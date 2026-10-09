<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import ComplianceWorkbench from '#lib/components/ComplianceWorkbench.svelte';
	import History from '#lib/components/History.svelte';
	import ResourceForm from '#lib/components/ResourceForm.svelte';
	import { resources } from '#lib/resources.ts';

	let { data } = $props();
	const can = (action: string, type = 'compliance.complianceassessment') => data.permissions.includes(`${type}:${action}`);
</script>

<svelte:head><title>{data.assessment.name}</title></svelte:head>

<p class="muted" style="margin-top: 20px"><a href="/r/compliance-assessments">Compliance assessments</a></p>
<h1>{data.assessment.name}</h1>
<p class="muted">Framework: <a href="/frameworks/{data.assessment.framework}">{data.assessment.framework_name}</a></p>

{#key data.assessment.id}
	<ComplianceWorkbench
		assessmentId={data.assessment.id}
		initialRows={data.rows}
		controls={data.controls}
		evidence={data.evidence}
		others={data.others}
		canChange={can('change', 'compliance.requirementassessment')}
	/>
{/key}

<details class="card">
	<summary><strong>Assessment settings</strong></summary>
	{#key data.assessment.id}
		<ResourceForm
			resource={resources['compliance-assessments']}
			object={data.assessment}
			domains={data.domains}
			people={data.people}
			refs={data.refs}
			canChange={can('change')}
			canDelete={can('delete')}
			onsaved={() => invalidateAll()}
			ondeleted={() => goto('/r/compliance-assessments')}
		/>
	{/key}
</details>

<section class="card">
	<h2>History</h2>
	<History events={data.trail} />
</section>
