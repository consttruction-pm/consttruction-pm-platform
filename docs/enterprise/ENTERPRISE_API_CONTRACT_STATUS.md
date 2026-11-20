# Enterprise Workbench — API Contract & Connection Status

Status date: 2026-11-20. Branch base: `main` @ `0014928`.

This document separates **mounted server capability** from **contracts the UI is
ready to consume**. A route is marked *registered* only after it answered on the
running preview; otherwise it is *unverified*. No endpoint below is simulated in
the client.

## 1. Session and shared reads (registered)

| Method | Path | State | Evidence | Used by |
| --- | --- | --- | --- | --- |
| GET | `/api/session` | registered, 200 | returns `user_id`, `tenant_id`, `roles` | shell, pages 2–15 |
| POST | `/api/session` | registered in production composition; 404 on the demo preview | production credentials only; preview uses `/preview/login` | page 2 production form |
| DELETE | `/api/session` | registered in production composition | sign-out | shell |
| GET | `/api/projects` | registered, 200 | project summaries with `revision` | pages 4, 7, 8, 10, 13, 14 |
| GET | `/api/projects/{id}/p6/resources` | registered, 200 | `p6-resource-api.v1` | pages 8, 13 |
| GET | `/api/projects/{id}/p6/resource-capacities` | registered, 200 | `p6-resource-capacity-read-api.v1`, segments nested under `capacity` | page 13 |
| GET | `/api/projects/{id}/documents` | registered, 200 | `documents[]` | pages 6, 8 |
| GET | `/api/projects/{id}/risks` | registered, 200 | `p6-risk-api.v1` | pages 6, 8 |
| GET | `/api/projects/{id}/p6/issues` | registered, 200 | `p6-issue-api.v1` | pages 6, 8 |
| GET | `/api/projects/{id}/reports/catalogue` | registered, 200 | `subjects[]` with `label`, `fields` | pages 8, 14 |
| GET | `/api/projects/{id}/reports` | registered, 200 | `catalogue[]`; stored definitions carry `report_id` | pages 8, 14 |
| GET | `/api/projects/{id}/reports/{report_id}/runs` | registered in route table; empty until a definition exists | runs list | page 14 |
| GET | `/api/projects/{id}/reports/{report_id}/schedules` | registered in route table | schedules list | page 14 |
| POST | `/api/projects/{id}/reports/{report_id}/run` | registered in route table | existing runtime run | page 14 |
| GET | `/api/knowledge/cards` | registered, 200 | `{cards: []}` on the fresh preview database | page 15 |
| GET | `/api/knowledge/coverage` | registered, 200 | `cubi-knowledge-coverage.v1` | page 15 |
| GET | `/api/knowledge/search?q=` | registered, 200 | `hits[]`, `insufficient_knowledge` | page 15 |
| GET | `/api/forms/organization/overview` | registered, 200 | `cubi-form-builder-api.v1` | page 15 |

### Preview-only routes (not part of the product contract)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/preview/health` | capability probe used to decide whether the demo panel is shown |
| POST | `/preview/login` | issues a demo session for a fixed persona; `next` accepts `/app…` and local `/cubi…` paths |
| GET/DELETE | `/preview/logout`, `/preview/private-login` | existing preview session management |

## 2. Enterprise contracts (declared, not yet mounted)

These paths are used by the UI. On the current preview they answer
`404 ROUTE_NOT_FOUND`, and every page renders an explicit *Source not connected*
state. Registering them requires no UI rewrite: the pages already probe and
render availability.

### 2.1 Enterprise tasks — `cubi-enterprise-task.v1`

Owner: Enterprise. The domain/repository/HTTP layer exists in the repository
body but depends on PostgreSQL advisory locks and triggers; it is not wired into
the SQLite preview.

| Method | Path | Request | Response | Conflict rules |
| --- | --- | --- | --- | --- |
| GET | `/api/enterprise/tasks?project_id=` | — | `{contract_version, tasks[]}` | 403 when project scope is denied |
| POST | `/api/enterprise/tasks` | `{contract_version, project_id, title, priority, assigned_user_id?, assigned_team_id?, due_date?, description?}` + `Idempotency-Key` | `{task}` 201 | duplicate key returns the original task |
| PATCH | `/api/enterprise/tasks/{task_id}` | `{contract_version, expected_revision, …patch}` | `{task}` | 409 `TASK_REVISION_CONFLICT` on stale revision |

Task fields used by page 10: `task_id`, `title`, `status`, `priority`,
`project_id`, `assigned_user_id`, `assigned_team_id`, `due_date`, `description`,
`revision`, `updated_at`. The page never derives these from P6 activities.

### 2.2 Dashboards and portlets

| Method | Path | Response contract | Page |
| --- | --- | --- | --- |
| GET | `/api/enterprise/dashboards` | `{dashboards[]}` with `dashboard_id`, `name`, `revision`, `visibility`, `portlets[]` | 4, 6 |
| GET/PUT | `/api/enterprise/dashboards/{dashboard_id}` | revision-checked document | 6 |
| POST | `/api/enterprise/dashboards/{dashboard_id}/share` | `{visibility, members[]}` | 6 (currently not called; visibility is device-local and labelled) |
| GET | `/api/enterprise/portlets/schedule-health?project_id=` | capability/read-model payload | 6 |
| GET | `/api/enterprise/portlets/evm-summary?project_id=` | Engineering-owned read model | 6 |
| GET | `/api/enterprise/portlets/resource-capacity?project_id=` | Engineering-owned read model | 6 |

Until these are mounted, layout persistence is intentionally device-local under
`cubi.enterprise.dashboards.v1`, with a local `revision`, and the UI states
"Server sync: not connected". No request is sent that pretends to save a shared
layout.

### 2.3 Portfolio, indicators and decisions

| Method | Path | Response contract | Page |
| --- | --- | --- | --- |
| GET | `/api/enterprise/portfolios` | portfolio register | 7 |
| GET | `/api/enterprise/portfolio/indicators?project_id=` | `{indicators[]}`; each indicator must carry `source`, `as_of`, `revision` | 7 |
| GET | `/api/enterprise/portfolio/trends?project_id=` | `{series[]}` with provenance | 7 |
| GET | `/api/enterprise/decisions` | `{decisions[]}` with revision | 7 |
| GET | `/api/enterprise/evm/capability` | capability descriptor from Engineering | 7 |

The Enterprise client never computes KPI, EVM, cost, resource or progress values.
If a route is absent, the row shows the source state; no substitute number is
shown.

### 2.4 Organization and access

| Method | Path | Entity |
| --- | --- | --- |
| GET | `/api/enterprise/organizations` | organizations |
| GET | `/api/enterprise/users` | users |
| GET | `/api/enterprise/teams` | teams |
| GET | `/api/enterprise/memberships` | memberships |
| GET | `/api/enterprise/invitations` | invitations |
| GET | `/api/enterprise/roles` | roles |
| GET | `/api/enterprise/grants` | grants |
| GET | `/api/enterprise/audit` | audit entries |

Required server rules: tenant scoping on every read/write, IDOR checks on every
path identifier, role checks for mutation, audit records for access changes. The
page displays these requirements and never asserts them as satisfied.

### 2.5 Workflows

| Method | Path | Contract |
| --- | --- | --- |
| GET | `/api/enterprise/workflows` | `{workflows[]}` with `workflow_id`, `version`, `definition`, `status` |
| POST | `/api/enterprise/workflows` | create draft (server-owned id) |
| POST | `/api/enterprise/workflows/{id}/versions` | add immutable version |
| POST | `/api/enterprise/workflows/{id}/publish` | publish an exact version |

The UI enforces structural validation locally (`validate()`), stores drafts on
the device, and disables Publish with an explicit reason until these routes are
mounted.

### 2.6 Approvals and feedback

| Method | Path | Contract |
| --- | --- | --- |
| GET | `/api/enterprise/approvals` | `{items[]}` with `item_id`, `revision`, `status` |
| GET | `/api/enterprise/feedback` | `{feedback[]}` |
| POST | `/api/enterprise/approvals/{item_id}/decisions` | `{expected_revision, decision, comment}` + `Idempotency-Key` |

Server rules required by page 12: reject a stale revision with `409`, reject a
duplicate decision with `409`, reject unauthorized decisions with `403`, and
record actor + revision. The UI distinguishes these statuses and never reports a
decision as recorded unless the server returned success.

### 2.7 Reports jobs

The reporting and durable scheduling runtimes already exist.

| Method | Path | Owner |
| --- | --- | --- |
| POST | `/api/v1/schedule/projects/{id}/jobs` | Scheduling Core |
| GET | `/api/v1/schedule/projects/{id}/jobs/{job_id}` | Scheduling Core |
| GET | `/api/v1/schedule/projects/{id}/jobs/{job_id}/result` | Scheduling Core |
| POST | `/api/v1/schedule/projects/{id}/jobs/{job_id}/cancel` | Scheduling Core |

Page 14 reads a job by id only. It never submits a run, starts a worker or keeps
a local queue.

## 3. Capability state vocabulary

`probe(path)` maps a server answer to exactly one state; the UI never upgrades a
state on its own.

| State | HTTP | Meaning | UI |
| --- | --- | --- | --- |
| `available` | 2xx | route registered and authorized | data or an honest empty panel |
| `unauthenticated` | 401 | no valid session | session-required block |
| `forbidden` | 403 | session valid, permission denied | forbidden block |
| `unavailable` | 404 | route not mounted in this build | "Source not connected" + contract path |
| `error` | other / network | failure | error block + retry |

## 4. Authorization model used by the client

1. The server issues `cp_session` (HttpOnly) and `cp_csrf`; `x-csrf-token` is sent
   on mutations.
2. `enterprise_admin` / `enterprise_user` / `enterprise_viewer` are classified by
   `enterpriseTier()` for explanation only. The page never gates an action by
   that classification; the server decides.
3. Project roles and Enterprise roles remain separate. A `project_admin` without
   an enterprise role sees *Enterprise entitlement is not present*.
4. Every project-scoped read is performed by the server opening the project;
   the client never invents a tenant or project id.
5. IDOR and tenant-isolation cases are listed on page 9; they become testable
   only when the entity routes are registered.

## 5. Known gaps (honest status)

- The Enterprise task, dashboard, organization, workflow, approval, portfolio
  indicator and decision routes are **not mounted** on this preview. The pages
  are complete and show `unavailable` with the exact contract.
- Dashboard layout, workflow drafts and the role-preference value are
  device-local. Sharing and visibility are not enforced.
- The preview knowledge database starts empty: cards and search legitimately
  return no results, and coverage shows zero converted topics.
- P6 method/parity help links cover scheduling and portfolio concepts. CUBI-only
  fields are marked `HELP_REFERENCE_PENDING` in the help matrix.
- Long-form page copy is reviewed in English and Persian; the other eight
  locales use the shared dictionary and fall back to English for missing keys.
