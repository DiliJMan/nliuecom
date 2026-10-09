# Architecture

## Shape of the system

```
Browser  ->  SvelteKit server (port 5173)  ->  Django API (port 8000, local only)
                 |                                  |
          serves pages, adds                  SQLite (PostgreSQL-ready),
          security headers, proxies /api      files on disk
```

The browser talks to one origin. The SvelteKit server forwards `/api/*` to Django and returns the reply. Three results follow from that:

- The session cookie is first-party and `HttpOnly`, so page scripts cannot read it.
- Django needs no cross-origin (CORS) rules.
- The Django port can stay bound to `127.0.0.1`.

The proxy buffers each request body and sends it with a `Content-Length`, because Django's development server rejects chunked bodies. It caps bodies at 40 MB and forwards only a short list of request headers.

## Backend apps

| App | Responsibility |
|---|---|
| `core` | Object type registry, shared API base classes, error mapping, pagination |
| `accounts` | Users (email login, Argon2), user groups, sign-in throttling and lockout |
| `domains` | The domain tree, stored as a materialised path |
| `access` | Roles, role assignments, and the single policy module that answers "may this user do this here?" |
| `audit` | Append-only, hash-chained event log, per-object trail, verification command |
| `customfields` | Typed extra attributes per object type, scoped to a domain subtree |
| `attachments` | Uploaded files with a SHA-256 checksum, forced-download serving, integrity check |
| `frameworks` | Frameworks, their requirement trees, mappings between them, the importers and the loader |
| `assets` | Assets, with a dependency graph that cannot loop |
| `controls` | Applied controls and evidence |
| `risk` | Risk matrices, assessments and scenarios, with current and residual levels |
| `compliance` | Compliance assessments, one answer per requirement, summaries and hints |
| `tasks` | Tasks, recurrence and reminder emails |
| `dashboard` | One read-only summary, limited to what the caller can see |

### The object type registry

Each app registers its models once, with a key such as `domains.domain`, the allowed actions, and a function that finds the object's domain. Permissions, audit logging, custom fields and the role editor all read that registry. A new module therefore gains scoping, history and custom fields by registering its models, with no edits to the other apps.

### Domains

A domain stores `path`, for example `/<root id>/<child id>/<own id>/`. A subtree query is `path LIKE '<prefix>%'`, and the ancestors of a domain are the ids inside its own path. Moving a domain rewrites the paths below it inside one transaction. The model refuses cycles, duplicate sibling names, and nesting beyond 12 levels.

### Permissions

A role is a list of codes shaped `<object type>:<action>`. A role assignment ties a role to a user or a group at one domain, and the `recursive` flag extends it to every sub-domain.

Rules, in the order the policy applies them:

1. An instance administrator (`is_superuser`) may do anything.
2. Otherwise a code applies at a domain when an assignment (direct or through a group) names that domain, or an ancestor with `recursive` set, and the role contains the code.
3. Objects outside any domain (users, roles, groups) can be written by instance administrators only.
4. Listings are filtered in the database query, so rows outside a user's scope are absent. A request for such a row returns 404.
5. Creating an object needs `add` in the target domain. Moving an object, or a domain, needs `add` in the destination.
6. Assigning a role requires holding every permission that role carries, at that domain. No one can grant more than they have.

The five built-in roles (Reader, Contributor, Manager, Auditor, Domain administrator) are rebuilt after every migration, so object types added later join them. Built-in roles cannot be edited. Custom roles are available through the API.

### Audit log

Every create, update, delete, many-to-many change, sign-in, failed sign-in, sign-out and file download writes an `AuditEvent` with the actor, the address, the object, its domain, and a field-level before and after. Passwords and path fields are excluded.

Each event stores the hash of its predecessor and a SHA-256 over its own content. Four layers protect the log:

1. The model and queryset refuse `save` on an existing row, `update` and `delete`.
2. A database trigger (SQLite and PostgreSQL) rejects `UPDATE` and `DELETE` from any client, including raw SQL.
3. SQLite runs in `IMMEDIATE` transaction mode, so two writers cannot fork the chain.
4. `manage.py verify_audit_chain` recomputes the whole chain and names the first broken record.

The tests drop the trigger, edit a record, and confirm that verification catches it. They also delete a middle record and confirm the break.

A person with full control of the database file can drop the trigger and recompute every hash after an edit. To close that gap, the SIEM forwarding module planned for Phase 4 will also ship each event hash to a system the database administrator does not control. A keyed hash (HMAC) with a secret held outside the database is a second option.

### Custom fields

A definition names an object type, a key, a type (text, number, yes or no, date, single choice, multiple choice), and an optional domain. A definition without a domain applies everywhere. One with a domain applies to that subtree. A key can be defined only once along any root-to-leaf path, so values never collide. Values live in each object's `custom_fields` JSON column and are validated on every write: unknown keys, wrong types, bad dates, and values outside the choice list are rejected, and required fields are enforced.

### Attachments

The stored file name is generated, so a client cannot choose a path. Extensions are checked against an allow-list, size is capped, and the SHA-256 is taken at upload. Downloads are served as `application/octet-stream` with `Content-Disposition: attachment`, `nosniff`, and a sandboxing `Content-Security-Policy`, and each download is audited. `POST /api/attachments/<id>/verify/` recomputes the checksum from storage.

## Phase 1 modules

### Links between objects

A scenario names assets, evidence names controls, a task names whatever it is about. One rule covers all of them (`core/linking.py`): the linked object must sit in the same domain as the object or in one of its ancestors, and the person making the change must be allowed to view it. Without the rule, a link could carry data across domain boundaries that the permission model keeps apart. Choosing a framework for an assessment follows the same idea: only frameworks the user can see are accepted.

### Frameworks

A framework is a row plus a tree of `RequirementNode`s. An imported framework has no domain and is locked. A custom one has a domain, and its permissions follow that domain. Importers (`frameworks/importers`) turn a source file into a neutral `FrameworkSpec`; the loader writes it in one transaction. Each requirement may carry `extra["maps_to"]`, a list of references into other frameworks. `sync_mappings` turns those references into `RequirementMapping` rows whenever a framework is loaded, so links appear as soon as both ends exist.

Licensed and no-derivatives sources set `redistributable` to false. That flag blocks export and carries over to derived copies. See [frameworks.md](frameworks.md).

### Risk

A matrix holds the likelihood scale, the impact scale, the risk levels with their colours, and a grid that maps each pair to a level. It is validated on every save: dimensions, level indexes and colours. Scenarios store rating steps, and the level is worked out from the assessment's matrix when read, so editing a custom matrix never leaves stale levels behind. The matrix of an assessment cannot change once scenarios exist.

### Compliance

Creating an assessment adds one row per assessable requirement in a single bulk insert. The framework cannot change afterwards, and a framework in use cannot be deleted or replaced. The workbench endpoint returns the whole requirement tree with the answers. Hints take results from a second assessment and attach them to the unassessed requirements that map onto them.

### Tasks and reminders

A repeating task creates its next occurrence when completed, once, with month ends and leap days handled. `send_reminders` mails each assignee one message listing what needs attention: once when a task enters its reminder window, again on the due date, then weekly while overdue. It records what it sent, so running it twice in a day says nothing new. Mail goes through Django 6.1's `MAILERS` setting and prints to the console until `NLIUE_SMTP_HOST` is set.

### People pickers

Owner and assignee menus need a list of people, but only administrators may list users. `/api/auth/directory/` returns id, name and address of active users to anyone who holds a role (or is an administrator), so someone with no access yet cannot enumerate colleagues.

## Security properties

| Property | Where it comes from | Known gap |
|---|---|---|
| Confidentiality | Argon2 password hashes; scoped queries; `HttpOnly` same-site session cookie; CSRF token on every write; CSP, `nosniff`, frame denial; generic sign-in errors; 12-character password minimum with common-password checks | No multi-factor authentication yet (planned with SSO); `NLIUE_SECURE_COOKIES` must be set when serving over HTTPS |
| Integrity | Database constraints; validated uploads with checksums; custom field validation; audit chain; cross-domain link rules; matrix and importer self-checks; links limited to http and https | Chain and data share one database (see above) |
| Availability | Per-user and per-login rate limits; bounded request and upload sizes; local-only API port | Lockout after repeated failures can be used to lock out a known address for 15 minutes; instance administrators should have a second administrator account. Automated backups are planned |
| Authenticity | Session authentication; every event stores who acted | Multi-factor authentication and SSO planned |
| Accountability | Actor, address and time on every event; per-object trail; scoped global log | Forwarded addresses are trusted only when `NLIUE_TRUST_FORWARDED_FOR` is set |
| Non-repudiation | Append-only chained log with a database trigger; verification command | Signed, externally anchored hashes planned |
| Reliability | 153 backend tests, 6 frontend tests, browser tests run during development against real files, CI that also checks migrations and generated types | The browser tests are not yet part of CI |

## Extension points for later phases

- **Phase 1 modules** register their models in the object type registry and inherit scoping, history and custom fields.
- **SSO and SCIM** attach to `accounts`: a SAML or OIDC login view calls Django's `login()`, and a SCIM endpoint maps provider groups onto `UserGroup` rows. Role assignments already accept groups.
- **Webhooks and SIEM forwarding** subscribe to `audit.service.record`, which every event passes through.
- **PostgreSQL** needs a settings change only. The trigger migration already carries the PostgreSQL variant, and no query depends on SQLite behaviour.
