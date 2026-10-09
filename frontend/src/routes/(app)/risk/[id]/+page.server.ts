import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import type { Page, Schemas } from '#lib/api/client.ts';
import { getJson, loadCommon, loadPermissions, loadRefs } from '#lib/loaders.ts';
import { resources, scenarioFields, type Row } from '#lib/resources.ts';

type Heatmap = { matrix: Schemas['RiskMatrix']; current: number[][]; residual: number[][]; unrated: number };

export const load: PageServerLoad = async ({ fetch, params }) => {
	const response = await fetch(`/api/risk-assessments/${params.id}/`);
	if (!response.ok) error(response.status === 404 ? 404 : 403, 'Risk assessment not available');
	const assessment = (await response.json()) as Row;
	const resource = resources['risk-assessments'];
	const [heatmap, scenarios, common, assessmentRefs, scenarioRefs, permissions, trail] = await Promise.all([
		getJson<Heatmap | null>(fetch, `/api/risk-assessments/${params.id}/heatmap/`, null),
		getJson<Page<Row>>(fetch, `/api/risk-scenarios/?risk_assessment=${params.id}&page_size=500`, { count: 0, next: null, previous: null, results: [] }),
		loadCommon(fetch),
		loadRefs(fetch, resource.fields),
		loadRefs(fetch, scenarioFields({ probability: [], impact: [] })),
		loadPermissions(fetch, assessment.domain),
		getJson<Schemas['AuditEvent'][]>(fetch, `/api/audit/trail/risk.riskassessment/${params.id}/`, [])
	]);
	if (!heatmap) error(500, 'The risk matrix could not be loaded');
	return { assessment, heatmap, scenarios: scenarios.results, ...common, assessmentRefs, scenarioRefs, permissions, trail };
};
