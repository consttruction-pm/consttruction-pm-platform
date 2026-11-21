# Enterprise Workbench — API Contract & Connection Status

Status date: 2026-11-21. Branch: `feat/cubi-enterprise-workbench`. This supersedes
the first-delivery status where the `/api/enterprise/*` routes were described as
unmounted. It now covers all **25 initial-set pages** delivered on the preview
runtime.

This document separates **mounted server capability** from **contracts the UI is
ready to consume**. A route is *mounted* only after it answered on the running
preview with the real session; otherwise it is explicitly *not mounted*. No
endpoint below is simulated in the client, and no Engineering figure is
calculated by Enterprise.

## 1. Session and shared reads (mounted)

| Method | Path | State | Evidence | Used by |
| --- | --- | --- | --- | --- |
| GET | `/api/session` | mounted, 200 | returns `user_id`, `tenant_id`, `roles`, `expires_at` | shell, pages 2–15 |
| POST | `/api/session` | mounted in production composition; not on the demo preview | production credentials only; preview uses `/preview/login` | page 2 production form |
| DELETE | `/api/session` | mounted in production composition | sign-out | shell |
| GET | `/api/projects` | mounted, 200 | project summaries with `revision` | pages 4, 7, 8, 10, 13, 14 |
| GET | `/api/projects/{id}/p6/resources` | mounted, 200 | `p6-resource-api.v1` | pages 8, 13 |
| GET | `/api/projects/{id}/p6/resource-capacities` | mounted, 200 | `p6-resource-capacity-read-api.v1`, segments nested under `capacity` | page 13 |
| GET | `/api/projects/{id}/documents` | mounted, 200 | `documents[]` | pages 6, 8 |
| GET | `/api/projects/{id}/risks` | mounted, 200 | `p6-risk-api.v1` | pages 6, 8 |
| GET | `/api/projects/{id}/p6/issues` | mounted, 200 | `p6-issue-api.v1` | pages 6, 8 |
| GET | `/api/projects/{id}/reports/catalogue` | mounted, 200 | `subjects[]` with `label`, `fields` | pages 8, 14 |
| GET | `/api/projects/{id}/reports` | mounted, 200 | `catalogue[]`; stored definitions carry `report_id` | pages 8, 14 |
| GET | `/api/projects/{id}/reports/{report_id}/runs` | mounted, empty until a definition exists | runs list | page 14 |
| GET | `/api/projects/{id}/reports/{report_id}/schedules` | mounted | schedules list | page 14 |
| POST | `/api/projects/{id}/reports/{report_id}/run` | mounted, existing runtime | report run | page 14 |
| GET | `/api/knowledge/cards` | mounted, 200 | `{cards: []}` on the fresh preview database | page 15 |
| GET | `/api/knowledge/coverage` | mounted, 200 | `cubi-knowledge-coverage.v1` | page 15 |
| GET | `/api/knowledge/search?q=` | mounted, 200 | `hits[]`, `insufficient_knowledge` | page 15 |
| GET | `/api/forms/organization/overview` | mounted, 200 | `cubi-form-builder-api.v1` | page 15 |

### Entry routes

| Route | Behaviour |
| --- | --- |
| `/login` | Canonical sign-in document. In the preview it renders the persona card and preserves `next`; `/preview/login` remains a compatibility alias. |
| `/workbench/` | Personal Workbench, served from `apps/web/app.html` by the preview. Canonical signed-in entry to both environments. Sign-out returns to `/login`. |
| `/app` | Engineering workspace shell (unchanged). |
| `/cubi/*` | Enterprise Workbench shell (`apps/web/enterprise.html`), own client router. |
| `/enterprise` | Retired Engineering route: `308` to `/cubi/`, never `app.html`. |
| `/cubi/workbench`, `/cubi/environments` | Redirect to `/workbench/`; no parallel workbench is rendered. |

### Preview-only routes (not part of the product contract)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/preview/health` | capability probe used to decide whether the demo panel is shown |
| POST | `/preview/login` (alias `/login`) | issues a demo session for a fixed persona; `next` accepts `/app…`, `/workbench/` and local `/cubi…` paths |
| DELETE | `/api/session` | revokes the preview session and clears `cp_session`; `204` |
| POST | `/preview/logout` (alias `/logout`) | revokes the session and redirects to `/login` |
| GET/DELETE | `/preview/logout`, `/preview/private-login` | existing preview session management |

## 2. Enterprise API — mounted on the preview runtime

Two middleware layers own `/api/enterprise/*`:

- `EnterpriseTaskHttpMiddleware` owns `/api/enterprise/tasks*` (mature v1 contract,
  now backed by `SQLiteEnterpriseTaskRepository` in preview and PostgreSQL in
  production).
- `EnterpriseWorkbenchHttpMiddleware` owns every other `/api/enterprise/*` route
  through `EnterpriseWorkbenchStore`.

Both derive identity, tenant and roles from the `cp_session` cookie only. A
client-supplied `tenant_id` in a body is rejected with
`403 TENANT_IS_CLIENT_CONTROLLED`; a `tenant_id` query parameter is ignored and
the result stays tenant-scoped.

### 2.1 Tasks — `cubi-enterprise-task.v1`

| Method | Path | Behaviour |
| --- | --- | --- |
| GET | `/api/enterprise/tasks?project_id=` | personal list by default; project list when `project_id` is authorized |
| POST | `/api/enterprise/tasks` | `Idempotency-Key` required; replay with the same payload returns the original task |
| GET | `/api/enterprise/tasks/{task_id}` | tenant-scoped; unknown or cross-tenant id → 404 |
| PATCH | `/api/enterprise/tasks/{task_id}` | `expected_revision`; stale → `409 ENTERPRISE_TASK_REVISION_CONFLICT` |

Dependencies are cycle-checked; completion actor/time are server-owned. Delete is
**not** implemented for tasks (no route) and the UI does not offer it. Team
assignment and Engineering references remain rejected by the application service
until membership persistence and the authorized resolver exist.

### 2.2 Generic Enterprise records

Kinds: `organizations`, `users`, `teams`, `memberships`, `invitations`, `roles`,
`grants`, `workflows`, `approvals`, `feedback`, `portfolios`, `decisions`,
`dashboards`, `risks`, `documents`, `eps`, `timesheets`, `notifications`,
`settings`, `forms`, `directory`.

| Method | Path | Behaviour |
| --- | --- | --- |
| GET | `/api/enterprise/{kind}` | tenant-scoped list; filters `status`, `project_id`, `q`, `limit`, `include_deleted` (`1`/`true`/`yes`) |
| POST | `/api/enterprise/{kind}` | create with optional `Idempotency-Key`; required fields and kind-specific rules validated |
| GET | `/api/enterprise/{kind}/{id}` | 404 for unknown, deleted or cross-tenant records |
| PATCH | `/api/enterprise/{kind}/{id}` | `expected_revision`; immutable identity fields rejected with `400 IMMUTABLE_FIELDS`; stale → `409 REVISION_CONFLICT` |
| DELETE | `/api/enterprise/{kind}/{id}` | soft delete with `expected_revision`; row stays for audit |
| POST | `/api/enterprise/{kind}/{id}/restore` | restores a soft-deleted record; `409 RECORD_NOT_DELETED` otherwise |
| GET | `/api/enterprise/audit` | append-only audit events; write methods → `405` |

Required fields per kind: `risks.title`, `documents.title`, `eps.name`,
`timesheets.user_id` + `work_date` + `hours`, `notifications.title`,
`settings.key`, `forms.name` + `fields`, `directory.display_name`.

Kind-specific validation (applied on both create and PATCH):

| Kind | Rule | Error |
| --- | --- | --- |
| `risks` | `risk_type` ∈ `risk`, `issue` | `400 RISK_TYPE_INVALID` |
| `risks` | `severity` (when present) ∈ `low`, `medium`, `high`, `critical` | `400 SEVERITY_INVALID` |
| `timesheets` | `hours` numeric, `0 < hours ≤ 24` | `400 HOURS_INVALID` |
| `timesheets` | `work_date` matches `YYYY-MM-DD` | `400 WORK_DATE_INVALID` |
| `forms` | `fields` non-empty array of objects with a non-blank `name` | `400 FORM_FIELDS_REQUIRED` / `400 FORM_FIELD_INVALID` |

Role gates are server-side:

- read: `enterprise_viewer`, `enterprise_user` or `enterprise_admin`;
- write: `enterprise_user` or `enterprise_admin`;
- `organizations`, `users`, `teams`, `memberships`, `invitations`, `roles`,
  `grants`, `settings`, `forms`: `enterprise_admin` only.

Admin-only kinds stay readable by every enterprise tier and answer
`403 ENTERPRISE_ADMIN_REQUIRED` on write, so the access/settings pages can show
the record without inventing a mutation.

`directory` is the tenant contact directory backing the Directory page;
`audit` is read-only and has no create/edit/delete control in the client.
`eps` stores an Enterprise-side EPS structure only; the authoritative project
hierarchy stays in Engineering and is not duplicated here.

Preview fixtures seed only the tenant organization, the demo users, the role
catalogue and one `demo: true` team. Tasks, approvals, workflows, invitations,
grants and all other work records start empty, so the operator exercises real
writes instead of reading sample work items.

### 2.3 Approvals

| Method | Path | Behaviour |
| --- | --- | --- |
| GET | `/api/enterprise/approvals/{id}/decisions` | decision history for one approval |
| POST | `/api/enterprise/approvals/{id}/decisions` | `expected_revision` + `Idempotency-Key`; stale → `409 STALE_REVISION`; replaying any key → `409 DUPLICATE_DECISION`; success sets status and increments the approval revision |

A decision is a one-shot act: the same key is rejected even with an identical
payload, so an approval cannot be recorded twice.

### 2.4 Workflows

| Method | Path | Behaviour |
| --- | --- | --- |
| GET | `/api/enterprise/workflows` | draft and published workflows with revisions |
| POST | `/api/enterprise/workflows` | create draft |
| PATCH | `/api/enterprise/workflows/{id}` | edit draft with `expected_revision` |
| POST | `/api/enterprise/workflows/{id}/publish` | `expected_revision`; server validates ≥2 steps, unique ids, a terminal step, known/unique/non-self transitions and reachability; success stores `status=published` and increments `published_version` |

Invalid graphs return `400 WORKFLOW_INVALID:<reasons>`; a stale revision returns
`409 REVISION_CONFLICT`.

### 2.5 Dashboards

| Method | Path | Behaviour |
| --- | --- | --- |
| GET | `/api/enterprise/dashboards` | saved layouts for the tenant |
| POST | `/api/enterprise/dashboards` | create layout; returns `server_id`/`revision` |
| PATCH | `/api/enterprise/dashboards/{id}` | revision-checked update from the designer |

The browser keeps a local layout copy for instant paint and reports the server
revision only after the save succeeds. `visibility` is stored with the record as
metadata; preview does not enforce it as access control.

### 2.6 Engineering-derived routes (deliberately not fabricated)

| Method | Path | Answer | Reason |
| --- | --- | --- | --- |
| GET | `/api/enterprise/portlets*` | `503 ENGINEERING_SOURCE_NOT_CONNECTED` | Portlet values must come from a versioned Engineering read model |
| GET | `/api/enterprise/portfolio*` | `503 ENGINEERING_SOURCE_NOT_CONNECTED` | KPI/trend values belong to Engineering |
| GET | `/api/enterprise/evm*` | `503 ENGINEERING_SOURCE_NOT_CONNECTED` | EVM is Engineering-owned |

The client maps 503 to the `source_unavailable` state and shows *source not
connected*; no substitute number is rendered.

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
| `available` | 2xx | route mounted and authorized | data or an honest empty panel |
| `unauthenticated` | 401 | no valid session | session-required block |
| `forbidden` | 403 | session valid, permission denied | forbidden block |
| `unavailable` | 404 | route not mounted | "Source not connected" + contract path |
| `source_unavailable` | 503 | route mounted, Engineering source absent | "Source not connected"; no derived value |
| `error` | other / network | transient failure | error block + retry |

## 4. Authorization model used by the client

1. The server issues `cp_session` (HttpOnly) and sets `cp_csrf`; `x-csrf-token` is
   sent on mutations where the runtime requires it.
2. `enterprise_admin` / `enterprise_user` / `enterprise_viewer` are classified by
   `enterpriseTier()` for explanation only. The page never gates an action by
   that classification; the server decides.
3. Project roles and Enterprise roles remain separate. A `project_admin` without
   an enterprise role sees *Enterprise entitlement is not present*.
4. Every project-scoped read is performed by the server opening the project; the
   client never invents a tenant or project id.
5. Backend tests assert unauthenticated 401, non-enterprise 403, cross-tenant
   404, IDOR 404, client tenant override 403 and audit read-only 405.

## 5. Known gaps (honest status)

- Portlet, portfolio indicator/trend and EVM routes return
  `503 ENGINEERING_SOURCE_NOT_CONNECTED`; the required Engineering read models are
  not connected. No value is calculated in Enterprise.
- Task delete, team assignment and Engineering object references are not
  implemented; the API rejects them rather than faking support.
- Member Activities (page 19) is a **read-only** projection of
  `/api/projects/{id}/p6/activities`. It offers no create/edit/delete control and
  links out to Engineering for any change; it never writes activity data.
- `eps` records are an Enterprise-side structure only. They do not create,
  reorder or reorganize the authoritative Engineering EPS, which remains owned
  by Engineering.
- `directory` and `settings` are tenant-scoped collaboration data. `settings`
  stores key/value configuration for the tenant; it does not change server
  behaviour until a consumer reads the key, and no page claims otherwise.
- `forms` validates the field schema only (non-empty, named fields). Schema
  versioning, published-form immutability and submission storage are not part of
  this delivery.
- Invitation acceptance is not implemented; the access page marks that row
  *pending server route*.
- Dashboard visibility is stored but not enforced as access control in preview.
- The SQLite preview uses one connection and a runtime lock. Production
  PostgreSQL concurrency, advisory locks and triggers are **Unverified** here;
  the SQLite adapter is a preview implementation, not a production claim.
- Preview CSRF posture: the demo runtime relies on `SameSite=Lax` + HttpOnly
  session cookies; the CSRF header helper is present but preview login does not
  issue `cp_csrf`. This is a preview-only posture and must not be treated as
  production CSRF evidence.
- The preview knowledge database starts empty: cards and search legitimately
  return no results, and coverage shows zero converted topics.
- P6 help links cover the mapped concepts. CUBI-only fields are marked
  `HELP_REFERENCE_PENDING` in the help matrix.
- Long-form page copy is reviewed in English and Persian; the other eight locales
  use the shared dictionary and fall back to English for missing keys.


## 6. V26 addendum — entry routing, session sign-out and operational UI

Recorded 2026-11-21 on `feat/cubi-entry-enterprise-operational`.

1. **Preview canonical login.** `/login` now serves the same sign-in card as
   `/preview/login`; anonymous requests to `/app`, `/workbench/` and
   `/cubi/enterprise/*` redirect to `/login?next=…`. The post-login fallback is
   `/workbench/`. `/enterprise` answers `308` to `/cubi/`.
2. **Session termination.** `DELETE /api/session` revokes the preview session and
   answers `204`; the Personal Workbench and the Enterprise shell both return to
   `/login` after sign-out. A stale cookie no longer keeps `/login` in the
   "signed in" state.
3. **Workbench store surface.** `EnterpriseWorkbenchHttpMiddleware` serves
   `GET/POST /api/enterprise/{kind}` and `GET/PATCH/DELETE
   /api/enterprise/{kind}/{id}` plus `POST …/{id}/restore` for
   organizations, users, teams, memberships, invitations, roles, grants,
   workflows, approvals, feedback, portfolios, decisions, dashboards, risks,
   documents, eps, timesheets, notifications, settings, forms and directory.
   List filters: `q`, `status`, `project_id`, `include_deleted`, `limit`.
   `approvals/{id}/decisions`, `workflows/{id}/publish` and `audit` (read-only)
   are dedicated actions.
4. **Operating surface.** Registers share a toolbar/sort/selection/detail/context
   menu/CSV component; Portfolio, Projects, Tasks, Approvals, Dashboard, Workflow
   and Member Activities have page-specific controls. The top bar adds global
   search over served routes and readable projects (`Ctrl/Cmd+K`) and a
   notification indicator based on `/api/enterprise/notifications`.
5. **Production composition gap (unchanged blocker).** The production runtime
   still mounts only `EnterpriseTaskHttpMiddleware`. The `/api/enterprise/{kind}`
   workbench routes described above are mounted by the preview runtime; PR #2068
   tracks the production composition change. No production deployment or
   migration is claimed by this branch.
