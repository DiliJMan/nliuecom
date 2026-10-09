/** Describes each list-and-form resource once, so one set of components can show them all. */

export type Option = { value: string | number; label: string };
export type FieldKind =
	| 'text' | 'textarea' | 'number' | 'select' | 'intselect' | 'date' | 'bool'
	| 'domain' | 'user' | 'multi' | 'ref' | 'attachment';

export type Field = {
	key: string;
	label: string;
	kind: FieldKind;
	options?: Option[];
	/** Key of an entry in `refSources`, for 'multi' and 'ref' fields. */
	ref?: string;
	required?: boolean;
	help?: string;
	/** Shown when creating, then locked. */
	fixedOnEdit?: boolean;
	/** Starting value for a new object, matching the server's own default. */
	default?: string | number | boolean;
};

export type Column = {
	key: string;
	label: string;
	format?: 'domain' | 'user' | 'date' | 'enum' | 'percent' | 'text';
	options?: Option[];
};

export type RowAction = { label: string; path: (row: Row) => string; show?: (row: Row) => boolean };
export type Row = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export type Resource = {
	key: string;
	path: string;
	objectType: string;
	label: string;
	plural: string;
	intro: string;
	nameKey: string;
	columns: Column[];
	fields: Field[];
	supportsCustomFields: boolean;
	filters?: { key: string; label: string; options: Option[] }[];
	href?: (row: Row) => string;
	rowActions?: RowAction[];
	defaultFilter?: Record<string, string>;
};

export type RefSource = { path: string; label: (row: Row) => string };

export const refSources: Record<string, RefSource> = {
	assets: { path: '/api/assets/?page_size=500&ordering=name', label: (r) => r.name },
	'applied-controls': { path: '/api/applied-controls/?page_size=500&ordering=name', label: (r) => r.name },
	evidence: { path: '/api/evidence/?page_size=500&ordering=name', label: (r) => r.name },
	'risk-matrices': { path: '/api/risk-matrices/?page_size=100', label: (r) => r.name },
	frameworks: { path: '/api/frameworks/?page_size=200', label: (r) => `${r.name} ${r.version}`.trim() },
	attachments: { path: '/api/attachments/?page_size=500', label: (r) => r.original_name }
};

const opts = (pairs: [string | number, string][]): Option[] => pairs.map(([value, label]) => ({ value, label }));

export const assessmentStatus = opts([['planned', 'Planned'], ['in_progress', 'In progress'], ['in_review', 'In review'], ['done', 'Done']]);
const objective = opts([[1, '1 · Low'], [2, '2 · Medium'], [3, '3 · High'], [4, '4 · Very high']]);

export const resources: Record<string, Resource> = {
	assets: {
		key: 'assets', path: '/api/assets/', objectType: 'assets.asset', label: 'Asset', plural: 'Assets',
		intro: 'Processes, information, systems, sites and people worth protecting.',
		nameKey: 'name', supportsCustomFields: true,
		columns: [
			{ key: 'name', label: 'Name' },
			{ key: 'type', label: 'Type', format: 'enum', options: opts([['primary', 'Primary'], ['support', 'Supporting']]) },
			{ key: 'domain', label: 'Domain', format: 'domain' },
			{ key: 'owner', label: 'Owner', format: 'user' }
		],
		filters: [{ key: 'type', label: 'Type', options: opts([['primary', 'Primary'], ['support', 'Supporting']]) }],
		fields: [
			{ key: 'domain', label: 'Domain', kind: 'domain', required: true, fixedOnEdit: true },
			{ key: 'name', label: 'Name', kind: 'text', required: true },
			{ key: 'ref_id', label: 'Reference', kind: 'text' },
			{ key: 'type', label: 'Type', kind: 'select', options: opts([['support', 'Supporting (system, device, site, person)'], ['primary', 'Primary (process or information)']]) },
			{ key: 'description', label: 'Description', kind: 'textarea' },
			{ key: 'depends_on', label: 'Depends on', kind: 'multi', ref: 'assets', help: 'Assets this one relies on.' },
			{ key: 'owner', label: 'Owner', kind: 'user' },
			{ key: 'business_value', label: 'Business value', kind: 'text' },
			{ key: 'confidentiality', label: 'Confidentiality', kind: 'intselect', options: objective },
			{ key: 'integrity', label: 'Integrity', kind: 'intselect', options: objective },
			{ key: 'availability', label: 'Availability', kind: 'intselect', options: objective },
			{ key: 'link', label: 'Link', kind: 'text', help: 'An http or https address.' }
		]
	},
	'applied-controls': {
		key: 'applied-controls', path: '/api/applied-controls/', objectType: 'controls.appliedcontrol',
		label: 'Applied control', plural: 'Applied controls',
		intro: 'Measures the organisation actually runs: policies, procedures and safeguards.',
		nameKey: 'name', supportsCustomFields: true,
		columns: [
			{ key: 'name', label: 'Name' },
			{ key: 'status', label: 'Status', format: 'enum', options: opts([['to_do', 'To do'], ['planned', 'Planned'], ['in_progress', 'In progress'], ['active', 'Active'], ['on_hold', 'On hold'], ['deprecated', 'Deprecated']]) },
			{ key: 'category', label: 'Category', format: 'enum', options: opts([['policy', 'Policy'], ['process', 'Process'], ['technical', 'Technical'], ['physical', 'Physical'], ['procedure', 'Procedure']]) },
			{ key: 'eta', label: 'Target date', format: 'date' },
			{ key: 'domain', label: 'Domain', format: 'domain' }
		],
		filters: [{ key: 'status', label: 'Status', options: opts([['to_do', 'To do'], ['planned', 'Planned'], ['in_progress', 'In progress'], ['active', 'Active'], ['on_hold', 'On hold'], ['deprecated', 'Deprecated']]) }],
		fields: [
			{ key: 'domain', label: 'Domain', kind: 'domain', required: true, fixedOnEdit: true },
			{ key: 'name', label: 'Name', kind: 'text', required: true },
			{ key: 'ref_id', label: 'Reference', kind: 'text' },
			{ key: 'description', label: 'Description', kind: 'textarea' },
			{ key: 'status', label: 'Status', kind: 'select', options: opts([['to_do', 'To do'], ['planned', 'Planned'], ['in_progress', 'In progress'], ['active', 'Active'], ['on_hold', 'On hold'], ['deprecated', 'Deprecated']]) },
			{ key: 'category', label: 'Category', kind: 'select', options: opts([['', '(none)'], ['policy', 'Policy'], ['process', 'Process'], ['technical', 'Technical'], ['physical', 'Physical'], ['procedure', 'Procedure']]) },
			{ key: 'priority', label: 'Priority', kind: 'intselect', options: opts([[1, '1 · Most urgent'], [2, '2'], [3, '3'], [4, '4 · Least urgent']]) },
			{ key: 'effort', label: 'Effort', kind: 'select', options: opts([['', '(not estimated)'], ['xs', 'Extra small'], ['s', 'Small'], ['m', 'Medium'], ['l', 'Large'], ['xl', 'Extra large']]) },
			{ key: 'control_impact', label: 'Expected impact', kind: 'intselect', options: opts([[1, '1 · Slight'], [2, '2'], [3, '3'], [4, '4'], [5, '5 · Large']]), help: 'How much this control reduces risk.' },
			{ key: 'eta', label: 'Target date', kind: 'date' },
			{ key: 'expiry_date', label: 'Review or expiry date', kind: 'date' },
			{ key: 'owner', label: 'Owner', kind: 'user' },
			{ key: 'link', label: 'Link', kind: 'text', help: 'An http or https address.' }
		]
	},
	evidence: {
		key: 'evidence', path: '/api/evidence/', objectType: 'controls.evidence', label: 'Evidence', plural: 'Evidence',
		intro: 'Files and links that show a control works or a requirement is met.',
		nameKey: 'name', supportsCustomFields: true,
		columns: [
			{ key: 'name', label: 'Name' },
			{ key: 'attachment_name', label: 'File' },
			{ key: 'valid_until', label: 'Valid until', format: 'date' },
			{ key: 'domain', label: 'Domain', format: 'domain' }
		],
		fields: [
			{ key: 'domain', label: 'Domain', kind: 'domain', required: true, fixedOnEdit: true },
			{ key: 'name', label: 'Name', kind: 'text', required: true },
			{ key: 'description', label: 'Description', kind: 'textarea' },
			{ key: 'attachment', label: 'File', kind: 'attachment', help: 'Upload a file, or pick one already stored.' },
			{ key: 'url', label: 'Link', kind: 'text', help: 'An http or https address. A file, a link, or both.' },
			{ key: 'valid_until', label: 'Valid until', kind: 'date' },
			{ key: 'applied_controls', label: 'Supports controls', kind: 'multi', ref: 'applied-controls' }
		]
	},
	'risk-assessments': {
		key: 'risk-assessments', path: '/api/risk-assessments/', objectType: 'risk.riskassessment',
		label: 'Risk assessment', plural: 'Risk assessments',
		intro: 'Scenarios rated on a matrix, with current and residual risk.',
		nameKey: 'name', supportsCustomFields: true,
		href: (r) => `/risk/${r.id}`,
		columns: [
			{ key: 'name', label: 'Name' },
			{ key: 'status', label: 'Status', format: 'enum', options: assessmentStatus },
			{ key: 'scenario_count', label: 'Scenarios' },
			{ key: 'due_date', label: 'Due', format: 'date' },
			{ key: 'domain', label: 'Domain', format: 'domain' }
		],
		filters: [{ key: 'status', label: 'Status', options: assessmentStatus }],
		fields: [
			{ key: 'domain', label: 'Domain', kind: 'domain', required: true, fixedOnEdit: true },
			{ key: 'name', label: 'Name', kind: 'text', required: true },
			{ key: 'description', label: 'Description', kind: 'textarea' },
			{ key: 'matrix', label: 'Risk matrix', kind: 'ref', ref: 'risk-matrices', required: true },
			{ key: 'status', label: 'Status', kind: 'select', options: assessmentStatus },
			{ key: 'version', label: 'Version', kind: 'text' },
			{ key: 'eta', label: 'Target date', kind: 'date' },
			{ key: 'due_date', label: 'Due date', kind: 'date' },
			{ key: 'owner', label: 'Owner', kind: 'user' }
		]
	},
	'compliance-assessments': {
		key: 'compliance-assessments', path: '/api/compliance-assessments/', objectType: 'compliance.complianceassessment',
		label: 'Compliance assessment', plural: 'Compliance assessments',
		intro: 'A domain assessed against one framework, requirement by requirement.',
		nameKey: 'name', supportsCustomFields: true,
		href: (r) => `/compliance/${r.id}`,
		columns: [
			{ key: 'name', label: 'Name' },
			{ key: 'framework_name', label: 'Framework' },
			{ key: 'status', label: 'Status', format: 'enum', options: assessmentStatus },
			{ key: 'summary', label: 'Compliant', format: 'percent' },
			{ key: 'domain', label: 'Domain', format: 'domain' }
		],
		filters: [{ key: 'status', label: 'Status', options: assessmentStatus }],
		fields: [
			{ key: 'domain', label: 'Domain', kind: 'domain', required: true, fixedOnEdit: true },
			{ key: 'name', label: 'Name', kind: 'text', required: true },
			{ key: 'description', label: 'Description', kind: 'textarea' },
			{ key: 'framework', label: 'Framework', kind: 'ref', ref: 'frameworks', required: true, fixedOnEdit: true },
			{ key: 'status', label: 'Status', kind: 'select', options: assessmentStatus },
			{ key: 'version', label: 'Version', kind: 'text' },
			{ key: 'eta', label: 'Target date', kind: 'date' },
			{ key: 'due_date', label: 'Due date', kind: 'date' },
			{ key: 'owner', label: 'Owner', kind: 'user' }
		]
	},
	tasks: {
		key: 'tasks', path: '/api/tasks/', objectType: 'tasks.task', label: 'Task', plural: 'Tasks',
		intro: 'Work to do, with owners, due dates, repeats and email reminders.',
		nameKey: 'title', supportsCustomFields: true,
		columns: [
			{ key: 'title', label: 'Task' },
			{ key: 'status', label: 'Status', format: 'enum', options: opts([['to_do', 'To do'], ['in_progress', 'In progress'], ['done', 'Done'], ['cancelled', 'Cancelled']]) },
			{ key: 'due_date', label: 'Due', format: 'date' },
			{ key: 'assignee', label: 'Assigned to', format: 'user' },
			{ key: 'domain', label: 'Domain', format: 'domain' }
		],
		filters: [{ key: 'status', label: 'Status', options: opts([['to_do', 'To do'], ['in_progress', 'In progress'], ['done', 'Done'], ['cancelled', 'Cancelled']]) }],
		rowActions: [
			{ label: 'Mark done', path: (r) => `/api/tasks/${r.id}/complete/`, show: (r) => r.status === 'to_do' || r.status === 'in_progress' }
		],
		fields: [
			{ key: 'domain', label: 'Domain', kind: 'domain', required: true, fixedOnEdit: true },
			{ key: 'title', label: 'Title', kind: 'text', required: true },
			{ key: 'description', label: 'Description', kind: 'textarea' },
			{ key: 'assignee', label: 'Assigned to', kind: 'user' },
			{ key: 'status', label: 'Status', kind: 'select', options: opts([['to_do', 'To do'], ['in_progress', 'In progress'], ['done', 'Done'], ['cancelled', 'Cancelled']]) },
			{ key: 'priority', label: 'Priority', kind: 'intselect', default: 3, options: opts([[1, '1 · Most urgent'], [2, '2'], [3, '3 · Normal'], [4, '4 · Least urgent']]) },
			{ key: 'due_date', label: 'Due date', kind: 'date' },
			{ key: 'recurrence', label: 'Repeats', kind: 'select', options: opts([['none', 'Does not repeat'], ['daily', 'Daily'], ['weekly', 'Weekly'], ['monthly', 'Monthly'], ['yearly', 'Yearly']]), help: 'A repeating task needs a due date. Completing it creates the next one.' },
			{ key: 'recurrence_interval', label: 'Repeat every', kind: 'number', default: 1, help: 'Number of days, weeks, months or years.' },
			{ key: 'reminder_days_before', label: 'Remind (days before due)', kind: 'number', default: 1, help: 'An email goes to the assignee.' }
		]
	}
};

export const scenarioFields = (matrix: { probability: { name: string }[]; impact: { name: string }[] }): Field[] => {
	const steps = (items: { name: string }[]): Option[] => [{ value: '', label: '(not rated)' }, ...items.map((x, i) => ({ value: i, label: x.name }))];
	return [
		{ key: 'ref_id', label: 'Reference', kind: 'text' },
		{ key: 'name', label: 'Scenario', kind: 'text', required: true },
		{ key: 'description', label: 'Description', kind: 'textarea' },
		{ key: 'threats', label: 'Threats', kind: 'textarea' },
		{ key: 'vulnerabilities', label: 'Vulnerabilities', kind: 'textarea' },
		{ key: 'assets', label: 'Affected assets', kind: 'multi', ref: 'assets' },
		{ key: 'existing_controls', label: 'Existing measures (free text)', kind: 'textarea' },
		{ key: 'applied_controls', label: 'Applied controls', kind: 'multi', ref: 'applied-controls' },
		{ key: 'current_probability', label: 'Current likelihood', kind: 'intselect', options: steps(matrix.probability) },
		{ key: 'current_impact', label: 'Current impact', kind: 'intselect', options: steps(matrix.impact) },
		{ key: 'residual_probability', label: 'Residual likelihood', kind: 'intselect', options: steps(matrix.probability), help: 'After the applied controls.' },
		{ key: 'residual_impact', label: 'Residual impact', kind: 'intselect', options: steps(matrix.impact) },
		{ key: 'treatment', label: 'Treatment', kind: 'select', options: opts([['open', 'Not decided'], ['mitigate', 'Mitigate'], ['accept', 'Accept'], ['avoid', 'Avoid'], ['transfer', 'Transfer']]) },
		{ key: 'justification', label: 'Justification', kind: 'textarea' },
		{ key: 'owner', label: 'Owner', kind: 'user' }
	];
};

export const labelOf = (options: Option[] | undefined, value: unknown): string =>
	options?.find((o) => String(o.value) === String(value))?.label ?? String(value ?? '');

/** Custom (domain-owned) frameworks, edited through the same form as everything else. */
export const frameworkResource: Resource = {
	key: 'frameworks', path: '/api/frameworks/', objectType: 'frameworks.framework', label: 'Framework',
	plural: 'Frameworks', intro: '', nameKey: 'name', supportsCustomFields: false, columns: [],
	fields: [
		{ key: 'domain', label: 'Owning domain', kind: 'domain', required: true, fixedOnEdit: true },
		{ key: 'name', label: 'Name', kind: 'text', required: true },
		{ key: 'slug', label: 'Identifier', kind: 'text', required: true, help: 'Letters, numbers and hyphens. Unique within the domain.' },
		{ key: 'version', label: 'Version', kind: 'text' },
		{ key: 'provider', label: 'Provider', kind: 'text' },
		{ key: 'description', label: 'Description', kind: 'textarea' }
	]
};

export const nodeResource: Resource = {
	key: 'requirement-nodes', path: '/api/requirement-nodes/', objectType: 'frameworks.requirementnode',
	label: 'Requirement', plural: 'Requirements', intro: '', nameKey: 'name', supportsCustomFields: false, columns: [],
	fields: [
		{ key: 'ref_id', label: 'Reference', kind: 'text', required: true },
		{ key: 'name', label: 'Title', kind: 'text', required: true },
		{ key: 'description', label: 'Text', kind: 'textarea' },
		{ key: 'parent', label: 'Belongs under', kind: 'ref', ref: 'parents', help: 'Leave empty for a top-level entry.' },
		{ key: 'assessable', label: 'Assessed in compliance assessments (untick for a heading)', kind: 'bool' },
		{ key: 'weight', label: 'Weight (1 to 10)', kind: 'number', default: 1 },
		{ key: 'order', label: 'Position', kind: 'number', default: 0 }
	]
};
