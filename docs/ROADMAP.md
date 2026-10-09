# Roadmap

Each phase ends with a working, tested slice. Names under "Reference feature" are the capabilities you listed from the community project. The implementation is original in every case.

## Phase 0: Foundation (this repository)

| Reference feature | Status |
|---|---|
| Multi-level domain hierarchy | Done (API and tree view) |
| Fine-grained permissions per object type | Done (roles per domain, per action; custom roles through the API) |
| Custom fields | Done (API, rendered in the domain form) |
| Audit log and per-object audit trail | Done (API and pages) |
| User management and permissions | Done (users, groups, assignments) |
| Evidence and document management | Storage, checksums, download and verification done; upload screen follows in Phase 1 |
| API access | Done (REST, OpenAPI description) |
| Self-hosted deployment | Local run done; hosting guidance in Phase 4 |

Still open in Phase 0 and carried forward: visual role editor, custom field definition screens, attachment upload screen, TOTP multi-factor authentication, automated local backup.

## Phase 1: Core GRC (this repository)

| Reference feature | Status |
|---|---|
| Asset management | Done |
| Risk assessments | Done (configurable matrix, scenarios, current and residual ratings, heat maps, treatment) |
| Compliance management, multiple frameworks | Done (ISO/IEC 27001:2022 and SCF importers, mappings, workbench, hints) |
| Frameworks customisation | Done (derive, edit, nest, weights, project file export for open content) |
| Evidence and document management | Done (files and links, linked to controls and requirements) |
| Applied controls | Done |
| Tasks and reminders | Done (recurrence, email reminders through a daily command) |
| NIST CSF 2.0 | Waiting for the official data file (see docs/frameworks.md) |

Open items carried forward: an in-app role editor, custom field definition screens, TOTP multi-factor authentication, automated local backup, browser tests inside CI, and names instead of identifiers in history entries.

## Phase 2: Extended modules and reporting basics

Third-party risk management, business impact analysis, incident management, domain-level and instance-level analytics, export to CSV and Excel.

## Phase 3: Planning and prioritisation

Gantt timeline with dependencies, impact analysis across assets, risks and controls, effort-versus-impact review of controls, campaign management, focus mode for contributors, smart inspector for gaps and stale items.

## Phase 4: Integration and scale

SSO (SAML and OIDC), SCIM provisioning from IdP groups, advanced webhooks, audit log forwarding to a SIEM, Jira and ServiceNow synchronisation, data import wizard, domain export and import, PostgreSQL and hosting guidance.

## Phase 5: Reporting and branding

Custom branding, Word report templates, email templates.
