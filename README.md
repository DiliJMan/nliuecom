# nliuecom

A governance, risk and compliance workspace that runs on your own machine. Django provides the API; SvelteKit provides the web interface. Windows and Linux are both supported.

Phase 0 is the foundation:

- Nested domains for subsidiaries, business units, entities and teams
- Roles granted per domain, per object type and per action, with optional inheritance down the tree
- A tamper-evident audit log with a per-object history
- Custom fields that need no schema change
- Evidence attachments with checksums
- A REST API with a generated OpenAPI description

Phase 1 builds the core governance, risk and compliance modules on it:

- **Assets** with dependencies and security objectives
- **Risk assessments** on configurable matrices, with current and residual ratings and heat maps
- **Applied controls** and **evidence** (files, links), linked to controls and requirements
- **Frameworks**: import ISO/IEC 27001:2022 from your licensed PDF and the Secure Controls Framework from its workbook, build and derive your own, and follow mappings between them ([docs/frameworks.md](docs/frameworks.md))
- **Compliance assessments** with a requirement-by-requirement workbench and hints across frameworks
- **Tasks and reminders** with recurrence and email reminders
- A dashboard that summarises what you are allowed to see

The plan for the remaining modules is in [docs/ROADMAP.md](docs/ROADMAP.md). The design and its security properties are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

- Python 3.12 or newer
- Node.js 22.17 or newer (a SvelteKit 3 requirement)

## Quick start

```sh
python scripts/run.py setup --email you@example.com   # installs, migrates, creates the first administrator
python scripts/run.py dev                              # web app on http://127.0.0.1:5173
```

On Windows, use `py scripts\run.py ...` if `python` is not on the path. The password prompt appears during `setup`. To skip the prompt, set `NLIUE_ADMIN_PASSWORD` first.

Other commands:

| Command | What it does |
|---|---|
| `python scripts/run.py serve` | Builds the web app and runs it without file watching |
| `python scripts/run.py test` | Lint, backend tests, type checks and frontend tests |
| `python scripts/run.py manage verify_audit_chain` | Walks the audit log and reports the first broken record |
| `python scripts/run.py manage import_framework <scf\|iso27001\|project> <file>` | Loads a framework from a file you hold |
| `python scripts/run.py manage send_reminders` | Emails task reminders. Run it once a day from cron or Task Scheduler |

## Layout

```
backend/    Django project (apps: accounts, domains, access, audit, customfields, attachments, frameworks, assets, controls, risk, compliance, tasks, dashboard, core)
frontend/   SvelteKit application; src/lib/api/schema.d.ts is generated from openapi.yml
scripts/    run.py, the cross-platform launcher
docs/       architecture, frameworks, roadmap, reference policy
```

## Keeping generated files current

After any API change, regenerate the schema and the TypeScript types. CI fails when they drift.

```sh
cd backend && .venv/bin/python manage.py spectacular --file ../frontend/openapi.yml
cd ../frontend && npm run gen:api
```

## Licence

GNU Affero General Public License, version 3 (the latest published version), or any later version: SPDX `AGPL-3.0-or-later`. The full text is in [LICENSE](LICENSE).

Section 13 of the AGPL gives users of a network service the right to obtain its source. The footer of every page links to it; set `NLIUE_SOURCE_URL` if you host a modified copy somewhere else.

[docs/reference-policy.md](docs/reference-policy.md) explains how this project relates to the community project that inspired it.
