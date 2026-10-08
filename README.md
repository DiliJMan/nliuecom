# nliuecom

A governance, risk and compliance workspace that runs on your own machine. Django provides the API; SvelteKit provides the web interface. Windows and Linux are both supported.

This repository holds **Phase 0**, the foundation every later module builds on:

- Nested domains for subsidiaries, business units, entities and teams
- Roles granted per domain, per object type and per action, with optional inheritance down the tree
- A tamper-evident audit log with a per-object history
- Custom fields that need no schema change
- Evidence attachments with checksums
- A REST API with a generated OpenAPI description, and a web interface for the above

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
| `python backend/manage.py verify_audit_chain` | Walks the audit log and reports the first broken record |

## Layout

```
backend/    Django project (apps: accounts, domains, access, audit, customfields, attachments, core)
frontend/   SvelteKit application; src/lib/api/schema.d.ts is generated from openapi.yml
scripts/    run.py, the cross-platform launcher
docs/       architecture, roadmap, reference policy
```

## Keeping generated files current

After any API change, regenerate the schema and the TypeScript types. CI fails when they drift.

```sh
cd backend && .venv/bin/python manage.py spectacular --file ../frontend/openapi.yml
cd ../frontend && npm run gen:api
```

## Licence

This repository's `LICENSE` file currently holds the GNU GPL v3 text. Choose the licence you want before publishing. [docs/reference-policy.md](docs/reference-policy.md) explains how this project relates to the community project that inspired it.
