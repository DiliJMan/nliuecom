import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { Page, Schemas } from '#lib/api/client.ts';
import type { WorkRow } from '#lib/components/ComplianceWorkbench.svelte';
import { getJson, loadCommon, loadPermissions, loadRefs } from '#lib/loaders.ts';
import { resources, type Row } from '#lib/resources.ts';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const response = await fetch(`/api/compliance-assessments/${params.id}/`);
	if (!response.ok) error(response.status === 404 ? 404 : 403, 'Assessment not available');
	const assessment = (await response.json()) as Row;
	const resource = resources['compliance-assessments'];
	const none = { count: 0, next: null, previous: null, results: [] };
	const [rows, controls, evidence, others, common, refs, permissions, trail] = await Promise.all([
		getJson<WorkRow[]>(fetch, `/api/compliance-assessments/${params.id}/workbench/`, []),
		getJson<Page<Row>>(fetch, '/api/applied-controls/?page_size=500&ordering=name', none),
		getJson<Page<Row>>(fetch, '/api/evidence/?page_size=500&ordering=name', none),
		getJson<Page<Row>>(fetch, '/api/compliance-assessments/?page_size=100&ordering=name', none),
		loadCommon(fetch),
		loadRefs(fetch, resource.fields),
		loadPermissions(fetch, assessment.domain),
		getJson<Schemas['AuditEvent'][]>(fetch, `/api/audit/trail/compliance.complianceassessment/${params.id}/`, [])
	]);
	return {
		assessment, rows, ...common, refs, permissions, trail,
		controls: controls.results.map((c) => ({ id: c.id as string, label: c.name as string })),
		evidence: evidence.results.map((e) => ({ id: e.id as string, label: e.name as string })),
		others: others.results.filter((o) => o.id !== params.id).map((o) => ({ id: o.id as string, name: `${o.name} (${o.framework_name})` }))
	};
};
