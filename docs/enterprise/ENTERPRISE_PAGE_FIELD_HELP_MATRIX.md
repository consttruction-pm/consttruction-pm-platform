# Enterprise Workbench — Page & Field Help Reference Matrix

This hand-authored matrix is the **authoritative delivery matrix** for the 25
Enterprise pages. An earlier generated 16-row traceability table
(`scripts/generate_master_page_matrices.py`, contract
`cubi-enterprise-page-field-help-matrix.v1`) is preserved as
`ENTERPRISE_PAGE_FIELD_HELP_MATRIX.generated.json` and
`ENTERPRISE_TRACEABILITY_MATRIX_GENERATED.md`; it is input material, not the
delivery status of record, and the generator now writes to those names so it
cannot overwrite this file.

Scope: the 25 initial-set Enterprise Workbench pages served under `/cubi/*` from
`apps/web/enterprise.html` and `apps/web/src/enterprise/`.

Help baseline: Oracle Primavera P6 EPPM Help Version 26.

- Official table of contents (TOC): <https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm>
- Direct topic URL pattern: `https://docs.oracle.com/cd/G48897_01/p6help/en/<topic>.htm`
- Every direct URL below was read from the official TOC (`toc.htm`) response.
- `HELP_REFERENCE_PENDING` means no official P6 topic could be matched to that
  CUBI-owned field. The TOC remains the fallback; no URL is invented.

Engineering reference: CUBI Engineering owns schedule, activities, CPM, WBS,
resources, cost, progress and EVM. Engineering Help uses the Oracle P6 client
help TOC <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm>; the
Engineering workspace itself is out of scope for this Enterprise page matrix.
Every Enterprise field that delegates to Engineering is labelled as a delegated
read and is never calculated on the Enterprise side.

Legend for **Permission**: `server` means the value is enforced by the server on
the cited API; the page only explains it. `read` / `write` describe the action
the control performs; they are never a client-side grant.

## Delivery status (live, 2026-11-21)

Statuses follow the required vocabulary: **MISSING**, **IN_PROGRESS**,
**WIRED_READ**, **WIRED_WRITE**, **VERIFIED**. `VERIFIED` is used only where all
functional and Help requirements for the page are complete; a mounted route or a
green HTTP status alone is not enough.

| # | Page | Route | Status | What is real | What remains |
|---|------|-------|--------|--------------|--------------|
| 1 | CUBI Homepage | `/cubi/` | **VERIFIED** | Static product copy, official Help links, locale switching, browser pass | — |
| 2 | Login / Authentication | `/cubi/login` | **WIRED_WRITE** | Preview persona login issues a real `cp_session`; production form targets `/api/session` | Production credential flow not exercisable in the demo preview |
| 3 | Role & Permission Selection | `/cubi/roles` | **WIRED_READ** | Session roles/tenant read from the server; tier explained, never asserted | No role-assignment write API |
| 4 | Personal Workbench Dashboard | `/cubi/workbench` → `/workbench/` | **VERIFIED** | Single canonical entry; enterprise card links to `/cubi/enterprise/dashboard`; server-authoritative environment probe with retry; sign-out returns to `/login` | — |
| 5 | Environment Selector | `/cubi/environments` → `/workbench/` | **VERIFIED** | Same canonical entry; no parallel workbench rendered | — |
| 6 | Enterprise Dashboard & Portlets | `/cubi/enterprise/dashboard` | **WIRED_WRITE** | Layout create/update on `/api/enterprise/dashboards`, revision-checked, designer add/remove/reorder/resize, portlet text filter and project scope, server badge after reload | Portlet values (schedule/EVM/capacity) return 503 until Engineering read models connect; visibility is metadata only |
| 7 | Portfolio & Executive Center | `/cubi/enterprise/portfolio` | **WIRED_WRITE** | Decisions create/list on `/api/enterprise/decisions`; register toolbar with server-text search, status filter and locale-aware sort; decision form persists after reload | KPI/trend/EVM routes 503 `ENGINEERING_SOURCE_NOT_CONNECTED`; no numbers are derived |
| 8 | Enterprise Projects / Project Portal | `/cubi/enterprise/projects` | **WIRED_READ** | Projects from `GET /api/projects`; register search, status filter and sort; six-tab project portal reads official project routes | No Enterprise project write here; EPS hierarchy has its own page (#18) |
| 9 | Organization & Access Center | `/cubi/enterprise/access` | **WIRED_WRITE** | Team, invitation and grant create; soft delete; tenant isolation, IDOR and admin gates covered by backend tests | Invitation acceptance not implemented; demo fixture rows are non-deletable |
| 10 | Team & Task Center | `/cubi/enterprise/tasks` | **WIRED_WRITE** | Create/complete/PATCH with revision and idempotency; personal and project scope; register shows real rows | No task delete, team assignment or Engineering references by design |
| 11 | Workflow Studio | `/cubi/enterprise/workflows` | **WIRED_WRITE** | Create draft and publish with server graph validation; `published_version` increments | No workflow approval/scheduling integration |
| 12 | Feedback & Approval Center | `/cubi/enterprise/approvals` | **WIRED_WRITE** | Queue reads approvals; New approval creates a queue item; Review fills the revision; decision accepted once, stale/duplicate 409 shown to the user | No reviewer assignment; feedback write form is minimal |
| 13 | Resources & Capacity | `/cubi/enterprise/resources` | **WIRED_READ** | Reads existing resource/capacity routes verbatim; no aggregation | No resource directory or assignment edit |
| 14 | Reports & Operations | `/cubi/enterprise/reports` | **WIRED_READ** | Existing catalogue/definitions/jobs routes only; no parallel queue or worker | Report authoring/run from Enterprise is not opened |
| 15 | Knowledge & PMBOK Center | `/cubi/enterprise/knowledge` | **WIRED_READ** | Real knowledge/forms routes | Seed is empty; no knowledge contribution write |

## Initial-set pages delivered (10)

These are the remaining pages of the original 25-page initial set. Each one is
served from `/cubi/*` by the same Enterprise shell, uses a real tenant-scoped
route, and carries a direct Help topic. Status vocabulary is unchanged.

| # | Page | Route | Status | Fields written | Help topic / direct URL | What is real | What remains |
|---|------|-------|--------|----------------|-------------------------|--------------|--------------|
| 16 | Risk & Issue Management | `/cubi/enterprise/risks` | **WIRED_WRITE** | title · risk_type · severity · owner · description · status | *About Risks* <https://docs.oracle.com/cd/G48897_01/p6help/en/6628.htm> | Create/edit/soft delete/restore on `/api/enterprise/risks`; server validates type and severity; audit recorded | Schedule and cost impact stay in Engineering; no risk score is calculated |
| 17 | Document & Information Management | `/cubi/enterprise/documents` | **WIRED_WRITE** | title · category · owner · link · description · status | *About Documents* <https://docs.oracle.com/cd/G48897_01/p6help/en/6620.htm> | Register of document identity and review state with revisions and audit | Binary storage is out of scope; the page states that instead of implying upload |
| 18 | EPS / Project Hierarchy | `/cubi/enterprise/eps` | **WIRED_WRITE** | name · code · parent_id · description · status | *About the Enterprise Project Structure (EPS)* <https://docs.oracle.com/cd/G48897_01/p6help/en/6621.htm> | CUBI-owned EPS register with parent reference, revision history and audit | No CPM rollup; project dates remain Engineering facts |
| 19 | Team Member My Activities | `/cubi/enterprise/member-activities` | **WIRED_READ** | — (read-only by design) | *About P6 Team Member Status Updates* <https://docs.oracle.com/cd/G48897_01/p6help/en/50904.htm> | Auto-selects the first authorized project, reads the authoritative `GET /api/projects/{id}/p6/activities` route, client-side search over returned rows, links back to Engineering | No write control; status updates are performed in Engineering |
| 20 | Timesheets & Time Reporting | `/cubi/enterprise/timesheets` | **WIRED_WRITE** | user_id · work_date · hours · project_id · note · status | *About Timesheets* <https://docs.oracle.com/cd/G48897_01/p6help/en/6610.htm> | Server validates hours (0 < h ≤ 24) and ISO dates on create and patch; soft delete and audit | P6 timesheet approval and actuals remain Engineering-owned |
| 21 | Notifications & Messaging | `/cubi/enterprise/notifications` | **WIRED_WRITE** | title · message · audience · channel · status | *About email Notifications* <https://docs.oracle.com/cd/G48897_01/p6help/en/6605.htm> | Notification records with audience and channel, revisions and audit | No external delivery is claimed unless the server reports it |
| 22 | Enterprise Administration Settings | `/cubi/enterprise/settings` | **WIRED_WRITE** | key · value · description · status | *About Application Settings* <https://docs.oracle.com/cd/G48897_01/p6help/en/36403.htm> | Admin-only writes; a non-administrator receives 403 `ENTERPRISE_ADMIN_REQUIRED` | Settings are tenant records; no application restart or provisioning action |
| 23 | Form Builder Integration | `/cubi/enterprise/forms` | **WIRED_WRITE** | name · description · fields (JSON) · status | *About User Defined Fields* <https://docs.oracle.com/cd/G48897_01/p6help/en/6599.htm> | Server rejects an empty or unnamed field list; admin-only writes; JSON parsed in the client before send | Form rendering into other pages is not opened |
| 24 | Audit & Activity Log | `/cubi/enterprise/audit` | **WIRED_READ** | — (append-only) | *About Table Auditing* <https://docs.oracle.com/cd/G48897_01/p6help/en/102813.htm> | Reads `GET /api/enterprise/audit`; `POST` answers 405 by design | No export or retention policy editor |
| 25 | Resource Directory & Assignments | `/cubi/enterprise/directory` | **WIRED_WRITE** | display_name · email · role_title · team · capacity_hours · status | *About Resources* <https://docs.oracle.com/cd/G48897_01/p6help/en/6640.htm> | Tenant directory records with revision history and audit | Calendars, units and rates stay authoritative in Engineering; no leveling |

Live verification for all 25 pages remains recorded in `artifacts/enterprise-preview/`
(screenshots `01`–`25`). The V26 entry-and-operations increment (2026-11-21)
re-verified the 20 Enterprise data routes end to end and its artefacts are in
`artifacts/enterprise-preview/v26/`:

- 20/20 routes opened by direct URL and survived a hard refresh with the same
  `h1`; back/forward restored Portfolio and Approvals correctly.
- 5/5 personas (Enterprise administrator, Project administrator, Planner,
  Viewer, New account) signed in to `/workbench/`; only the Enterprise
  administrator reached `/cubi/enterprise/dashboard/`, every other persona was
  redirected to `/workbench/`; sign-out returned to `/login` with `/api/session`
  answering 401, and re-login succeeded.
- Dashboard layout Save reached `/api/enterprise/dashboards` and the server-sync
  badge survived a reload.
- Persian switch produced `dir=rtl`, `lang=fa` and a localized `h1`; no
  horizontal overflow at 1366×768 or 1280×720 in either Persian or English.

The register pages share one config-driven component (`pages/records.ts`), so
the field contract is visible in one place.

---

## Page 1 — CUBI Homepage

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `home` |
| Route | `/cubi/` |
| CUBI component | `renderHome` (`pages/home.ts`) |
| API | `GET /api/session` (indirect boot probe only) |
| Data source | Static product copy owned by CUBI; no schedule, cost or resource fact |
| Permission | Public page; no project or Enterprise role required |
| Test ID | Entry is `#cubi-app`; visual sections carry class hooks only |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Environment cards | — | `HELP_REFERENCE_PENDING` — nearest official topic: *About the User Interface* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9031.htm>) | `/cubi/` → Environments | Two cards: Engineering, Enterprise | Public | `home.ts` environment grid | none | CUBI product copy |
| Plan comparison | — | `HELP_REFERENCE_PENDING` — CUBI commercial copy, not a P6 screen | `/cubi/` → Plans | Plan name, body, bullet list | Public | `home.ts` plans | none | CUBI product copy |
| Security panel | — | *About Security* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9001.htm>) | `/cubi/` → Security and support | Session, CSRF, tenant isolation, audit | Public | `home.ts` security card | none | CUBI security model |
| Sign-in entry | — | *About User Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6597.htm>) | `/cubi/` → Sign in | Primary button to `/cubi/login` | Public | `publicNav()` | none | CUBI identity route |
| Help entry | — | TOC (<https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm>) | `/cubi/` → Help | External link, new tab, `noopener` | Public | `publicHelpUrl()` | none | Official P6 help |

---

## Page 2 — Login / Authentication (P6 About Security)

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `login` |
| Route | `/cubi/login` |
| CUBI component | `renderLogin` (`pages/login.ts`) |
| API | `POST /api/session`, `GET /api/session`, `DELETE /api/session`; preview only: `POST /preview/login`, `GET /preview/health` |
| Data source | Server-issued session cookie `cp_session`; CSRF cookie `cp_csrf` |
| Permission | Server validates credentials, tenant and roles; the client stores none of them |
| Test IDs | `login-email`, `login-password`, `login-submit`, `login-error`, `login-preview-panel` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Work email | `login-email` | *About Users* (<https://docs.oracle.com/cd/G48897_01/p6help/en/43794.htm>) | `/cubi/login` → Work email | Email input, `autocomplete=username`, required | server: credential check | `login.ts` form | `POST /api/session` | Server identity store |
| Password | `login-password` | *About Security* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9001.htm>) | `/cubi/login` → Password | Password input + Show/Hide, `autocomplete=current-password` | server: credential check | `login.ts` password row | `POST /api/session` | Server identity store |
| Sign-in submit | `login-submit` | *About Security* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9001.htm>) | `/cubi/login` → Sign in | Submit button; disabled while pending | server; errors 401/403/0 are shown verbatim | `api.login` | `POST /api/session` | Session cookie |
| Sign-in error | `login-error` | *About User Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6597.htm>) | Appears under the password field | `role=alert`, hidden until a server failure | server | `login.ts` error block | `POST /api/session` | Server error code |
| Security facts | — | *About Security* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9001.htm>) | `/cubi/login` → right panel | HttpOnly cookie, server authorization, CSRF, audit | claim only, verified by server | `securityLine()` | none | CUBI security model |
| Preview identity | `login-preview-panel` | `HELP_REFERENCE_PENDING` — local demo fixture, not a P6 screen | Only when `GET /preview/health` returns 200 | Four demo personas posting to `/preview/login` | preview server issues the demo session; production login is unaffected | `previewPanel()` | `POST /preview/login` | Local preview SQLite |

---

## Page 3 — Role & Permission Selection

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `roles` |
| Route | `/cubi/roles` |
| CUBI component | `renderRoles` (`pages/roles.ts`) |
| API | `GET /api/session` (roles already returned by the server) |
| Data source | Server session roles; Enterprise policy matrix is explanatory |
| Permission | Selection is a preference only; it never grants access |
| Test IDs | `roles-access`, `roles-matrix`, `roles-preference` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Environment access cards | `roles-access` | *About User Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6597.htm>) | `/cubi/roles` → Access overview | Engineering / Enterprise / Personal cards with granted role chips | server: roles come from `/api/session` | `roles.ts` | `GET /api/session` | Server session |
| Enterprise policy matrix | `roles-matrix` | *About Roles* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6641.htm>) | `/cubi/roles` → Enterprise policy | Rows: viewer, user, admin; columns: read, write, administer | server; matrix is reference text | `roles.ts` matrix | none | Enterprise role contract |
| Preferred view | `roles-preference` | `HELP_REFERENCE_PENDING` — CUBI navigation preference | `/cubi/roles` → Preferred view | Select stored under `cubi.enterprise.preferred-view` | local preference only | `roles.ts` | none | `localStorage` |
| Continue | — | `HELP_REFERENCE_PENDING` — CUBI navigation | `/cubi/roles` → Continue | Buttons to `/app/`, dashboard or workbench | target page re-checks the server | `roles.ts` | none | Router |

---

## Page 4 — Personal Workbench Dashboard

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `workbench` |
| Route | `/cubi/workbench` |
| CUBI component | `renderWorkbench` (`pages/workbench.ts`) |
| API | `GET /api/projects`, `GET /api/enterprise/tasks`, `GET /api/enterprise/approvals`, `GET /api/enterprise/dashboards`, `GET /api/enterprise/organizations` |
| Data source | Server session; visible projects; Enterprise task/approval/dashboard/org sources when mounted |
| Permission | Each source is probed; 401/403/404 are displayed, never bypassed |
| Test IDs | `workbench-hero`, `workbench-projects`, `workbench-sources`, `workbench-tasks`, `workbench-links` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Personal greeting | `workbench-hero` | *About the User Interface* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9031.htm>) | `/cubi/workbench` → top | Display name, tier, tenant | server session | `workbench.ts` | `GET /api/session` | Server session |
| Visible projects | `workbench-projects` | *About Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm>) | `/cubi/workbench` → Projects | Table: name, status, domain, revision, dates | server: only returned projects | `api.listProjects` | `GET /api/projects` | Project lifecycle store |
| Source status | `workbench-sources` | `HELP_REFERENCE_PENDING` — CUBI capability model | `/cubi/workbench` → Source status | Chip per source with HTTP status and state | server probe | `connectionList()` | four Enterprise paths + `/api/projects` | Server routes |
| Personal tasks | `workbench-tasks` | *About P6 Team Member Status Updates* (<https://docs.oracle.com/cd/G48897_01/p6help/en/50904.htm>) | `/cubi/workbench` → My tasks | Table filtered by `assigned_user_id` | server: Enterprise task API | `workbench.ts` | `GET /api/enterprise/tasks` | Enterprise task store (PostgreSQL) |
| Quick links | `workbench-links` | TOC (<https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm>) | `/cubi/workbench` → Centers | Links to the 10 Enterprise centers | target re-checks server | `workbench.ts` | none | Router |

---

## Page 5 — Environment Selector

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `environments` |
| Route | `/cubi/environments` |
| CUBI component | `renderEnvironments` (`pages/environments.ts`) |
| API | `GET /api/session` |
| Data source | Session roles; ownership boundary is documentation |
| Permission | Enterprise cards state the server entitlement; navigation never grants it |
| Test IDs | `environments-grid`, `environments-boundaries` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Engineering card | `environments-grid` | *About the User Interface* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9031.htm>) | `/cubi/environments` → Engineering | Access state, owns scheduling/CPM/WBS, link `/app/` | project permissions checked by Engineering | `environmentAccess()` | `GET /api/session` | Server session |
| Enterprise card | `environments-grid` | *About User Interface Views* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6598.htm>) | `/cubi/environments` → Enterprise | Entitlement tier, link `/cubi/enterprise/dashboard` | requires `enterprise_*` | `environmentAccess()` | `GET /api/session` | Server session |
| Ownership boundary | `environments-boundaries` | *About Portfolios* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6611.htm>) and *About Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm>) | `/cubi/environments` → Boundary table | Engineering-owned vs Enterprise-owned rows | explanatory | `environments.ts` | none | Architecture contract |

---

## Page 6 — Enterprise Dashboard & Portlets

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `dashboard` |
| Route | `/cubi/enterprise/dashboard` |
| CUBI component | `renderDashboard` (`pages/dashboard.ts`) |
| API | `GET /api/projects`; portlet endpoints `/api/enterprise/portlets/*`, `/api/enterprise/tasks`, `/api/enterprise/approvals`, project documents/risks/reports |
| Data source | Saved layout: `localStorage` key `cubi.enterprise.dashboards.v1` (device-local, revisioned); portlet facts: server routes |
| Permission | Layout is device-local only; visibility is not enforced and is labelled as such; every portlet confirms server access |
| Test IDs | `dashboard-toolbar`, `dashboard-portlets`, `dashboard-designer` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dashboard selector | `dashboard-toolbar` | *Working with Dashboards* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm>) | `/cubi/enterprise/dashboard` → toolbar | Select: delivery, executive, governance | local layout selection | `dashboard.ts` | none | `localStorage` |
| Project filter | `dashboard-toolbar` | *About Filters* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9027.htm>) | Toolbar → Project | Select of visible projects | server filters each portlet | `dashboard.ts` | `GET /api/projects` | Project store |
| Text filter | `dashboard-toolbar` | *Working with Find, Search, and Filter Features* (<https://docs.oracle.com/cd/G48897_01/p6help/en/8329.htm>) | Toolbar → Filter | Text input | local view filter | `dashboard.ts` | none | Local |
| Refresh | `dashboard-toolbar` | *Working with Dashboards* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm>) | Toolbar → Refresh | Button | re-probes every portlet | `dashboard.ts` | all portlet routes | Server |
| Dashboard designer | `dashboard-designer` | *Customizing Dashboards* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7827.htm>) | Toolbar → Customize layout | Catalog + installed list, drag/drop, up/down, size, remove | local design; save is device-local | `dashboard.ts` | none | `localStorage` |
| Portlet catalog | `dashboard-designer` | *List of Portlets* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6667.htm>) | Designer → Catalog | 10 portlets with source labels | none | `dashboard.ts` | none | Static catalog |
| Layout size | `dashboard-designer` | *Configuring Dashboard Layout* (<https://docs.oracle.com/cd/G48897_01/p6help/en/32008.htm>) | Designer → Installed → Size | narrow / standard / wide | local | `dashboard.ts` | none | `localStorage` |
| Save layout | `dashboard-designer` | *Configuring Dashboard Content* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7831.htm>) | Designer → Save layout | Button with local revision | local only; "Server sync: not connected" | `dashboard.ts` | none | `localStorage` |
| Visibility | `dashboard-designer` | *Configuring Dashboard Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/32010.htm>) | Designer → Visibility | private / team / organization | not enforced; explicit warning | `dashboard.ts` | none | Local preference |
| Portlet: schedule health | `dashboard-portlets` | *About Portlets* (<https://docs.oracle.com/cd/G48897_01/p6help/en/36613.htm>) | Dashboard → Schedule health | Status + source + revision | server probe | `dashboard.ts` | `/api/enterprise/portlets/schedule-health` | Enterprise read model (unverified route) |
| Portlet: portfolio summary | `dashboard-portlets` | *Working with Portfolio View Scorecards* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9116.htm>) | Dashboard → Portfolio | Row counts and registrations only; no KPI calculation | server | `dashboard.ts` | `GET /api/projects` | Project store |
| Portlet: cost/EVM | `dashboard-portlets` | *About Project Performance Metrics* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44844.htm>) | Dashboard → EVM summary | Displays only what the source returns | Engineering-owned; no recalculation | `dashboard.ts` | `/api/enterprise/portlets/evm-summary` | Engineering read model (unverified) |
| Portlet: capacity | `dashboard-portlets` | *Analyzing Role Allocation (Capacity Planning)* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7855.htm>) | Dashboard → Capacity | Read-only, raw segments | Engineering-owned | `dashboard.ts` | `/api/enterprise/portlets/resource-capacity` | Engineering (unverified) |
| Portlet: tasks | `dashboard-portlets` | *About Team Collaboration on an Activity* (<https://docs.oracle.com/cd/G48897_01/p6help/en/65537.htm>) | Dashboard → Tasks | Counts only | server | `dashboard.ts` | `GET /api/enterprise/tasks` | Enterprise task store |
| Portlet: approvals | `dashboard-portlets` | *Reviewing Team Member Status Updates* (<https://docs.oracle.com/cd/G48897_01/p6help/en/51331.htm>) | Dashboard → Approvals | Counts only | server | `dashboard.ts` | `GET /api/enterprise/approvals` | Approval store (unverified) |
| Portlet: risks | `dashboard-portlets` | *Assessing Project Health* (<https://docs.oracle.com/cd/G48897_01/p6help/en/43938.htm>) | Dashboard → Risks | Real project risks | server | `dashboard.ts` | `GET /api/projects/{id}/risks` | Risk API |
| Portlet: documents | `dashboard-portlets` | *Working with Detail Windows* (<https://docs.oracle.com/cd/G48897_01/p6help/en/14474.htm>) | Dashboard → Documents | Real documents | server | `dashboard.ts` | `GET /api/projects/{id}/documents` | Document store |
| Portlet: reports | `dashboard-portlets` | *Configuring Report Settings* (<https://docs.oracle.com/cd/G48897_01/p6help/en/78291.htm>) | Dashboard → Reports | Real report definitions/runs | server | `dashboard.ts` | `GET /api/projects/{id}/reports` | Reporting runtime |
| Portlet: access snapshot | `dashboard-portlets` | *About User Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6597.htm>) | Dashboard → Access | Counts only when route exists | server | `dashboard.ts` | `GET /api/enterprise/users` | Access store (unverified) |
| Source stamp | `dashboard-portlets` | `HELP_REFERENCE_PENDING` — CUBI freshness contract | Each portlet footer | `Source · Revision · Updated` | reflects server payload | `sourceStamp()` | per portlet | Server payload |

---

## Page 7 — Portfolio & Executive Center

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `portfolio` |
| Route | `/cubi/enterprise/portfolio` |
| CUBI component | `renderPortfolio` (`pages/portfolio.ts`) |
| API | `GET /api/projects`, `/api/enterprise/portfolio/indicators`, `/api/enterprise/portfolio/trends`, `/api/enterprise/decisions`, `/api/enterprise/evm/capability` |
| Data source | Project register (real); indicators/trends/decisions are read-only and never calculated here |
| Permission | Server re-checks every route; forbidden/unavailable are distinct states |
| Test IDs | `portfolio-register`, `portfolio-summary`, `portfolio-hierarchy`, `portfolio-detail`, `portfolio-scorecard`, `portfolio-indicators`, `portfolio-decisions` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Portfolio register | `portfolio-register` | *Working with Portfolios* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6671.htm>) | `/cubi/enterprise/portfolio` → Register | Project rows with status, revision, dates | server: visible projects only | `portfolio.ts` | `GET /api/projects` | Project lifecycle store |
| Registration summary | `portfolio-summary` | `HELP_REFERENCE_PENDING` — CUBI counts, not KPIs | Register → Summary | Row counts only, labelled "not KPIs" | none | `portfolio.ts` | `GET /api/projects` | Project store |
| Hierarchy | `portfolio-hierarchy` | *About EPS Views* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44832.htm>) | Portfolio → Hierarchy | Groups by `business_domain` | server list | `portfolio.ts` | `GET /api/projects` | Project store |
| Decision context | `portfolio-detail` | *Opening Portfolios* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7866.htm>) | Select a project | Detail list of project facts | server | `portfolio.ts` | `GET /api/projects` | Project store |
| Executive scorecard | `portfolio-scorecard` | *Working with Portfolio View Scorecards* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9116.htm>) | Portfolio → Scorecard | Schedule / Cost-EVM / Resources rows with source state | display only; no calculation | `portfolio.ts` | source probes | Engineering sources |
| KPI indicators | `portfolio-indicators` | *About Project Performance Metrics* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44844.htm>) | Portfolio → Indicators | Each indicator carries source, date, revision | read; never computed client-side | `portfolio.ts` | `/api/enterprise/portfolio/indicators` | Enterprise read model (unverified) |
| Trends | `portfolio-indicators` | *Assessing Project Performance* (<https://docs.oracle.com/cd/G48897_01/p6help/en/43935.htm>) | Portfolio → Trends | Trend capability probe | read | `portfolio.ts` | `/api/enterprise/portfolio/trends` | Enterprise read model (unverified) |
| Decisions | `portfolio-decisions` | *Working with Portfolio Views* (<https://docs.oracle.com/cd/G48897_01/p6help/en/14090.htm>) | Portfolio → Decisions | Decision register capability | read/write decided by server | `portfolio.ts` | `/api/enterprise/decisions` | Decision store (unverified) |
| EVM capability | `portfolio-indicators` | *About Metrics and Calculations* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6606.htm>) | Portfolio → EVM source | Capability chip only | Engineering-owned | `portfolio.ts` | `/api/enterprise/evm/capability` | Engineering (unverified) |

---

## Page 8 — Enterprise Projects / Project Portal

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `projects` |
| Route | `/cubi/enterprise/projects` |
| CUBI component | `renderProjects` (`pages/projects.ts`) |
| API | `GET /api/projects`; project-scoped resources, documents, risks, issues, reports; `GET …/p6/workspace` probe |
| Data source | Official project-scoped routes only; schedule detail stays in Engineering |
| Permission | Server opens the project and checks authorization on every tab |
| Test IDs | `projects-register`, `projects-portal`; tabs are buttons inside the portal |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Project register | `projects-register` | *Working with Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6693.htm>) | `/cubi/enterprise/projects` | Table with Open portal link per row | server: visible projects | `projects.ts` | `GET /api/projects` | Project store |
| Overview tab | `projects-portal` | *About Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm>) | Portal → Overview | Two-column details, source stamp | server | `projects.ts` | `GET /api/projects` | Project store |
| Engineering source tab | `projects-portal` | *About Activity Views* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6615.htm>) | Portal → Engineering source | Probes workspace, issues, earned value; links `/app/` | Engineering-owned; no recomputation | `projects.ts` | `/p6/workspace`, `/p6/issues`, `/p6/earned-value` | Engineering |
| Resources tab | `projects-portal` | *Analyzing Role Allocation (Capacity Planning)* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7855.htm>) | Portal → Resources | Resource table with revision | read-only | `projects.ts` | `GET …/p6/resources` | Engineering read model |
| Documents tab | `projects-portal` | *Working with Detail Windows* (<https://docs.oracle.com/cd/G48897_01/p6help/en/14474.htm>) | Portal → Documents | Document table | server | `projects.ts` | `GET …/documents` | Document store |
| Risks & issues tab | `projects-portal` | *Assessing Project Health* (<https://docs.oracle.com/cd/G48897_01/p6help/en/43938.htm>) | Portal → Risks & issues | Two registers | server | `projects.ts` | `GET …/risks`, `GET …/p6/issues` | Risk and issue APIs |
| Reports tab | `projects-portal` | *Configuring Report Settings* (<https://docs.oracle.com/cd/G48897_01/p6help/en/78291.htm>) | Portal → Reports | Definitions + catalogue | server | `projects.ts` | `GET …/reports`, `/reports/catalogue` | Reporting runtime |
| Open portal | — | *Opening Projects or Templates* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7978.htm>) | Register row | Link carrying `?project=<id>` | server | `pageHref` | none | Router |

---

## Page 9 — Organization & Access Center

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `access` |
| Route | `/cubi/enterprise/access` |
| CUBI component | `renderAccess` (`pages/access.ts`) |
| API | `GET /api/session`; probes for organizations, users, teams, memberships, invitations, roles, grants, audit |
| Data source | Server session scope; eight entity registers are read-only; isolation checks are documented expectations |
| Permission | No client-side permission logic; no fabricated users; tenant/IDOR checks are labelled as pending server routes where absent |
| Test IDs | `access-session`, `access-connections`, `access-policy`, `access-registers`, `access-isolation` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Session scope | `access-session` | *About User Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6597.htm>) | `/cubi/enterprise/access` → top | User, tenant, roles | server | `access.ts` | `GET /api/session` | Server session |
| Connection register | `access-connections` | `HELP_REFERENCE_PENDING` — CUBI capability model | Access → Source status | Chip per entity route | server probe | `access.ts` | eight Enterprise paths | Server routes |
| Enterprise role policy | `access-policy` | *Assigning Global Security Profiles* (<https://docs.oracle.com/cd/G48897_01/p6help/en/8117.htm>) and *Assigning Module Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/8118.htm>) | Access → Policy | Reference table | server; UI never grants | `access.ts` | none | Enterprise policy |
| Organizations | `access-registers` | *About Users* (<https://docs.oracle.com/cd/G48897_01/p6help/en/43794.htm>) | Access → Registers | Entity register, empty or denied | server | `access.ts` | `GET /api/enterprise/organizations` | Organization store (unverified) |
| Users | `access-registers` | *Adding Users in Native Authentication Mode* (<https://docs.oracle.com/cd/G48897_01/p6help/en/54061.htm>) | Access → Registers | User register | server | `access.ts` | `GET /api/enterprise/users` | Identity store (unverified) |
| Teams | `access-registers` | *About Resource Teams* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44162.htm>) | Access → Registers | Team register | server | `access.ts` | `GET /api/enterprise/teams` | Team store (unverified) |
| Memberships | `access-registers` | *Assigning OBS Elements to Users* (<https://docs.oracle.com/cd/G48897_01/p6help/en/35460.htm>) | Access → Registers | Membership register | server | `access.ts` | `GET /api/enterprise/memberships` | Membership store (unverified) |
| Invitations | `access-registers` | `HELP_REFERENCE_PENDING` — CUBI invitation flow | Access → Registers | Invitation register | server | `access.ts` | `GET /api/enterprise/invitations` | Invitation store (unverified) |
| Roles | `access-registers` | *About Roles* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6641.htm>) | Access → Registers | Role register | server | `access.ts` | `GET /api/enterprise/roles` | Role store (unverified) |
| Grants | `access-registers` | *About User Access* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6597.htm>) | Access → Registers | Grant register | server | `access.ts` | `GET /api/enterprise/grants` | Grant store (unverified) |
| Audit | `access-registers` | *About Table Auditing* (<https://docs.oracle.com/cd/G48897_01/p6help/en/102813.htm>) and *Viewing Audit Data* (<https://docs.oracle.com/cd/G48897_01/p6help/en/102814.htm>) | Access → Registers | Audit register | server | `access.ts` | `GET /api/enterprise/audit` | Audit store (unverified) |
| Tenant isolation / IDOR | `access-isolation` | *Configuring Audit Settings* (<https://docs.oracle.com/cd/G48897_01/p6help/en/89307.htm>) | Access → Isolation tests | Expected outcome per case; "pending server route" where missing | server-side only; never asserted as passed | `access.ts` | entity routes | Server authorization |

---

## Page 10 — Team & Task Center

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `tasks` |
| Route | `/cubi/enterprise/tasks` |
| CUBI component | `renderTasks` (`pages/tasks.ts`) |
| API | `GET/POST /api/enterprise/tasks`, `PATCH /api/enterprise/tasks/{id}`; contract `cubi-enterprise-task.v1` |
| Data source | Enterprise task store (PostgreSQL advisory locks/triggers); distinct from P6 activities and timesheets |
| Permission | Server authorizes create/update; Idempotency-Key on create; `expected_revision` on PATCH; 409 stale is shown |
| Test IDs | `tasks-intro`, `tasks-capability`, `tasks-filters`, `tasks-register`, `tasks-table`, `tasks-create-form`, `tasks-contract` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scope note | `tasks-intro` | *About P6 Team Member Status Updates* (<https://docs.oracle.com/cd/G48897_01/p6help/en/50904.htm>) | `/cubi/enterprise/tasks` → intro | Text: generic tasks are not P6 activities/timesheets | explanatory | `tasks.ts` | none | Contract |
| Task capability | `tasks-capability` | `HELP_REFERENCE_PENDING` — CUBI capability model | Tasks → source status | Chip + HTTP status | server probe | `tasks.ts` | `GET /api/enterprise/tasks` | Task API |
| Project filter | `tasks-filters` | *About Filters* (<https://docs.oracle.com/cd/G48897_01/p6help/en/9027.htm>) | Tasks toolbar | Project select | server query `project_id` | `tasks.ts` | `GET /api/enterprise/tasks?project_id=` | Task store |
| Status filter | `tasks-filters` | *Filtering Data* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44870.htm>) | Tasks toolbar | Status select | local view filter | `tasks.ts` | none | Loaded rows |
| Priority filter | `tasks-filters` | *Filtering Data* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44870.htm>) | Tasks toolbar | Priority select | local view filter | `tasks.ts` | none | Loaded rows |
| Search | `tasks-filters` | *Searching for Entries* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7818.htm>) | Tasks toolbar | Text input | local view filter | `tasks.ts` | none | Loaded rows |
| New task | `tasks-create-toggle` | *Creating, Modifying, Saving, and Deleting Data* (<https://docs.oracle.com/cd/G48897_01/p6help/en/8331.htm>) | Tasks toolbar → New task | Button, disabled while the route is absent | server on submit | `tasks.ts` | `POST /api/enterprise/tasks` | Task store |
| Title | `tasks-create-title` | `HELP_REFERENCE_PENDING` — CUBI task field | Create form | Required text | server | `tasks.ts` | `POST /api/enterprise/tasks` | Task store |
| Priority | `tasks-create-priority` | `HELP_REFERENCE_PENDING` — CUBI task field | Create form | low / normal / high / critical | server | `tasks.ts` | `POST /api/enterprise/tasks` | Task store |
| Project | `tasks-create-project` | *About Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm>) | Create form | Select of visible projects | server | `tasks.ts` | `POST /api/enterprise/tasks` | Project store |
| Assigned user | `tasks-create-assignee` | *About Activity Owners* (<https://docs.oracle.com/cd/G48897_01/p6help/en/51373.htm>) | Create form | Text user id | server resolves assignment | `tasks.ts` | `POST /api/enterprise/tasks` | Task store |
| Assigned team | `tasks-create-team` | *About Resource Teams* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44162.htm>) | Create form | Text team id | server resolves team | `tasks.ts` | `POST /api/enterprise/tasks` | Team store |
| Due date | `tasks-create-due` | *Working with Tables* (<https://docs.oracle.com/cd/G48897_01/p6help/en/14490.htm>) | Create form | Date input | server | `tasks.ts` | `POST /api/enterprise/tasks` | Task store |
| Description | `tasks-create-description` | *About Data Entry Controls* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44204.htm>) | Create form | Textarea | server | `tasks.ts` | `POST /api/enterprise/tasks` | Task store |
| Assigned Team column | `tasks-table` | *About Resource Teams* (<https://docs.oracle.com/cd/G48897_01/p6help/en/44162.htm>) | Register → Assigned team | Real team id or "Unassigned" | server value | `tasks.ts` | `GET /api/enterprise/tasks` | Task store |
| Revision-checked update | `tasks-table` | *Creating, Modifying, Saving, and Deleting Data* (<https://docs.oracle.com/cd/G48897_01/p6help/en/8331.htm>) | Row action → status change | Sends `expected_revision`; 409 STALE shown | server conflict check | `api.updateTask` | `PATCH /api/enterprise/tasks/{id}` | Task store |
| Contract reference | `tasks-contract` | `HELP_REFERENCE_PENDING` — CUBI Enterprise Task API v1 | Tasks → contract panel | Idempotency, revision, roles | documentation of server rules | `tasks.ts` | none | `CUBI_ENTERPRISE_TASK_API_V1.md` |

---

## Page 11 — Workflow Studio

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `workflows` |
| Route | `/cubi/enterprise/workflows` |
| CUBI component | `renderWorkflows` (`pages/workflows.ts`) |
| API | `GET /api/enterprise/workflows` (probe only); drafts stored under `cubi.enterprise.workflow.draft.v1` |
| Data source | Device-local draft with revision; publish requires a server route and stays disabled |
| Permission | Publish is never simulated; validation is pure and deterministic |
| Test IDs | `workflows-intro`, `workflows-capability`, `workflows-editor`, `workflows-canvas`, `workflows-validation`, `workflows-step-name` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scope note | `workflows-intro` | `HELP_REFERENCE_PENDING` — no official P6 workflow studio topic; use TOC (<https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm>) | `/cubi/enterprise/workflows` | Versioned draft explanation | explanatory | `workflows.ts` | none | Contract |
| Service capability | `workflows-capability` | `HELP_REFERENCE_PENDING` — CUBI workflow service | Workflows → source status | Chip + status | server probe | `workflows.ts` | `GET /api/enterprise/workflows` | Workflow service (unverified) |
| Workflow name | `workflows-step-name` | `HELP_REFERENCE_PENDING` — CUBI workflow field | Editor → Name | Text input | local until publish | `workflows.ts` | none | Draft |
| Step name | `workflows-step-name` | `HELP_REFERENCE_PENDING` — CUBI workflow field | Editor → Steps | Text per step, terminal toggle | local | `workflows.ts` | none | Draft |
| Remove step | `workflows-editor` | `HELP_REFERENCE_PENDING` — CUBI workflow field | Steps → Remove | Button | local | `workflows.ts` | none | Draft |
| Add transition | `workflows-editor` | `HELP_REFERENCE_PENDING` — CUBI workflow field | Transitions → Add | From/to selects, label | local | `workflows.ts` | none | Draft |
| Flow canvas | `workflows-canvas` | `HELP_REFERENCE_PENDING` — CUBI visual designer | Editor → Canvas | Nodes and labelled edges | local | `workflows.ts` | none | Draft |
| Validate | `workflows-validation` | `HELP_REFERENCE_PENDING` — CUBI rule set | Editor → Validate | Result list: name, ≥2 steps, unique ids/names, terminal, missing/self/duplicate transitions, reachability | local, deterministic | `validate()` | none | Draft |
| Save draft | `workflows-editor` | `HELP_REFERENCE_PENDING` — CUBI local persistence | Editor → Save draft | Writes local revision | device-local only | `workflows.ts` | none | `localStorage` |
| Publish | `workflows-editor` | `HELP_REFERENCE_PENDING` — requires server route | Editor → Publish | Disabled with explicit reason | server would enforce | `workflows.ts` | none | — |

---

## Page 12 — Feedback & Approval Center

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `approvals` |
| Route | `/cubi/enterprise/approvals` |
| CUBI component | `renderApprovals` (`pages/approvals.ts`) |
| API | `GET /api/enterprise/approvals`, `GET /api/enterprise/feedback`, `POST /api/enterprise/approvals/{id}/decisions` |
| Data source | Approval/feedback stores when mounted; decisions pinned to an expected revision |
| Permission | Server enforces decision rights, revision and duplicate protection; 403/404/409/network are distinct |
| Test IDs | `approvals-intro`, `approvals-queue`, `approvals-decision`, `approvals-item-id`, `approvals-outcomes`, `approvals-feedback` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scope note | `approvals-intro` | *Approving or Rejecting Timesheets* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7847.htm>) — related P6 approval only | `/cubi/enterprise/approvals` | Text distinguishing generic approvals from timesheets | explanatory | `approvals.ts` | none | Contract |
| Approval queue | `approvals-queue` | *Reviewing Team Member Status Updates* (<https://docs.oracle.com/cd/G48897_01/p6help/en/51331.htm>) | Approvals → Queue | Table of items | server | `approvals.ts` | `GET /api/enterprise/approvals` | Approval store (unverified) |
| Item ID | `approvals-item-id` | `HELP_REFERENCE_PENDING` — CUBI approval item | Decision form | Text input | server resolves item | `approvals.ts` | `POST …/decisions` | Approval store |
| Expected revision | `approvals-revision` | `HELP_REFERENCE_PENDING` — CUBI revision guard | Decision form | Number input | server rejects stale/duplicate (409) | `approvals.ts` | `POST …/decisions` | Approval store |
| Decision | `approvals-outcome` | *Accepting Team Member Status Updates* (<https://docs.oracle.com/cd/G48897_01/p6help/en/100563.htm>) | Decision form | approve / reject / request changes | server | `approvals.ts` | `POST …/decisions` | Approval store |
| Comment | `approvals-comment` | *Having a Discussion with Team Members* (<https://docs.oracle.com/cd/G48897_01/p6help/en/62939.htm>) | Decision form | Textarea | server | `approvals.ts` | `POST …/decisions` | Approval store |
| Submit decision | `approvals-decision` | *Rejecting Team Member Status Updates* (<https://docs.oracle.com/cd/G48897_01/p6help/en/100561.htm>) | Decision form → Submit | Idempotency-Key + CSRF header; 409/403/404 shown | server | `approvals.ts` | `POST /api/enterprise/approvals/{id}/decisions` | Approval store |
| Decision outcomes | `approvals-outcomes` | *Viewing Team Member Status Updates History* (<https://docs.oracle.com/cd/G48897_01/p6help/en/51471.htm>) | Below the form | Outcome table | server | `approvals.ts` | `GET /api/enterprise/approvals` | Approval store |
| Feedback | `approvals-feedback` | *Sharing Your Feedback With Us* (<https://docs.oracle.com/cd/G48897_01/p6help/en/113132.htm>) | Approvals → Feedback | Feedback register | server | `approvals.ts` | `GET /api/enterprise/feedback` | Feedback store (unverified) |

---

## Page 13 — Resources & Capacity

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `resources` |
| Route | `/cubi/enterprise/resources` |
| CUBI component | `renderResources` (`pages/resources.ts`) |
| API | `GET /api/projects/{id}/p6/resources`, `GET /api/projects/{id}/p6/resource-capacities` |
| Data source | Engineering read models, displayed raw with `project_revision` |
| Permission | Read-only; no aggregation, leveling, rate, cost or utilisation calculation on the client |
| Test IDs | `resources-intro`, `resources-context`, `resources-register`, `resources-capacity` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Read-only notice | `resources-intro` | *Analyzing Role Allocation (Capacity Planning)* (<https://docs.oracle.com/cd/G48897_01/p6help/en/7855.htm>) | `/cubi/enterprise/resources` | Warning: no aggregation/leveling/rates/cost | explanatory | `resources.ts` | none | Engineering boundary |
| Project selector | — | *About Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm>) | Resources → Project scope | Select navigating with `?project=` | server scopes the read | `resources.ts` | `GET /api/projects` | Project store |
| Project context | `resources-context` | *Working with Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6693.htm>) | Resources → Context | Project, revision, status, manager | server | `resources.ts` | `GET /api/projects` | Project store |
| Resource register | `resources-register` | *About Assignments Views* (<https://docs.oracle.com/cd/G48897_01/p6help/en/66168.htm>) | Resources → Register | Name, type, unit, calendar, email, active, revision | read-only | `resources.ts` | `GET …/p6/resources` | Engineering read model |
| Capacity segments | `resources-capacity` | *Assigning Resources or Roles to Projects or WBS Elements* (<https://docs.oracle.com/cd/G48897_01/p6help/en/100879.htm>) and *Allocating Units to Resources or Roles* (<https://docs.oracle.com/cd/G48897_01/p6help/en/100881.htm>) | Resources → Capacity | From, to, max units, unit basis, hours/period, project revision | read-only | `resources.ts` | `GET …/p6/resource-capacities` | Engineering capacity segments |
| Source stamp | `resources-capacity` | `HELP_REFERENCE_PENDING` — CUBI freshness contract | Section footer | `Source · Revision · Updated` | reflects payload | `sourceStamp()` | per read model | Engineering payload |

---

## Page 14 — Reports & Operations

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `reports` |
| Route | `/cubi/enterprise/reports` |
| CUBI component | `renderReports` (`pages/reports.ts`) |
| API | `GET …/reports/catalogue`, `GET …/reports`, `GET …/reports/{report_id}/runs`, `GET …/reports/{report_id}/schedules`, `POST …/reports/{report_id}/run`, `GET /api/v1/schedule/projects/{id}/jobs/{job_id}` |
| Data source | Existing reporting runtime and existing durable scheduling job queue; no second queue, worker or cron |
| Permission | Server checks project authorization and report permissions; job lookup is read-only |
| Test IDs | `reports-intro`, `reports-runtime`, `reports-catalogue`, `reports-definitions`, `reports-operations`, `reports-jobs`, `reports-jobs-panel`, `reports-run` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scope note | `reports-intro` | *Configuring Report Settings* (<https://docs.oracle.com/cd/G48897_01/p6help/en/78291.htm>) | `/cubi/enterprise/reports` | Text: existing runtime, no parallel queue | explanatory | `reports.ts` | none | Contract |
| Project scope | — | *About Projects* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6636.htm>) | Reports → Project scope | Select navigating with `?project=` | server scopes runtime | `reports.ts` | `GET /api/projects` | Project store |
| Runtime capability | `reports-runtime` | `HELP_REFERENCE_PENDING` — CUBI capability model | Reports → Runtime capability | Catalogue and definition chips | server probe | `reports.ts` | two report routes | Reporting runtime |
| Report catalogue | `reports-catalogue` | *Working with Tables* (<https://docs.oracle.com/cd/G48897_01/p6help/en/14490.htm>) | Reports → Catalogue | Subjects, field counts | server | `api.reportCatalogue` | `GET …/reports/catalogue` | Reporting runtime |
| Definition list | `reports-definitions` | *Creating, Modifying, Saving, and Deleting Data* (<https://docs.oracle.com/cd/G48897_01/p6help/en/8331.htm>) | Reports → Definitions | Table with revision and Inspect link | server; only rows with `report_id` shown | `api.listReports` | `GET …/reports` | Reporting runtime |
| Run history | `reports-operations` | *Working with Tables* (<https://docs.oracle.com/cd/G48897_01/p6help/en/14490.htm>) | Select a definition | Run table | server | `api.listReportRuns` | `GET …/reports/{id}/runs` | Reporting runtime |
| Schedules | `reports-operations` | *Publishing P6 Data* (<https://docs.oracle.com/cd/G48897_01/p6help/en/48619.htm>) — related scheduling concept | Select a definition | Schedule table | server | `api.listReportSchedules` | `GET …/reports/{id}/schedules` | Reporting runtime |
| Run report | `reports-run` | *Configuring Report Settings* (<https://docs.oracle.com/cd/G48897_01/p6help/en/78291.htm>) | Definition → Run report | Button + status line | server; nothing queued locally | `api.runReport` | `POST …/reports/{id}/run` | Reporting runtime |
| Existing job routes | `reports-jobs` | `HELP_REFERENCE_PENDING` — CUBI durable job contract | Reports → Existing scheduling job queue | Table: submit, status, result, cancel | Engineering-owned Scheduling Core | `reports.ts` | `/api/v1/schedule/projects/{id}/jobs…` | Scheduling Core |
| Job id | `reports-jobs-panel` | `HELP_REFERENCE_PENDING` — CUBI job lookup | Jobs → Existing job id | Text input + Read job | server | `readJob()` | `GET …/jobs/{job_id}` | Scheduling Core |
| Job detail | `reports-jobs-panel` | `HELP_REFERENCE_PENDING` — CUBI job view | After Read job | State, attempts, engine, revision, updated | server | `jobDetail()` | `GET …/jobs/{job_id}` | Scheduling Core |

---

## Page 15 — Knowledge & PMBOK Center

**Record**

| Attribute | Value |
| --- | --- |
| Page ID | `knowledge` |
| Route | `/cubi/enterprise/knowledge` |
| CUBI component | `renderKnowledge` (`pages/knowledge.ts`) |
| API | `GET /api/knowledge/cards`, `GET /api/knowledge/coverage`, `GET /api/knowledge/search?q=`, `GET /api/forms/organization/overview` |
| Data source | Platform knowledge service (CUBI-owned cards, official source URLs) and shared Form Builder library |
| Permission | `KNOWLEDGE_READ` is checked by the server; form authoring stays in the existing Form Builder |
| Test IDs | `knowledge-intro`, `knowledge-capability`, `knowledge-search`, `knowledge-cards`, `knowledge-coverage`, `knowledge-forms` |

**Fields**

| Field | Test ID | Help topic / direct URL | Getting Here | Screen Elements | Permission | CUBI component | API | Data source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scope note | `knowledge-intro` | *About P6 Help* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6602.htm>) | `/cubi/enterprise/knowledge` | Text: CUBI-owned, one shared form engine | explanatory | `knowledge.ts` | none | CUBI knowledge policy |
| Knowledge capability | `knowledge-capability` | `HELP_REFERENCE_PENDING` — CUBI capability model | Knowledge → Service | Chips: cards, coverage, Form Builder | server probe | `knowledge.ts` | three knowledge routes + form overview | Platform services |
| Search query | `knowledge-search-input` | *About Find, Search, and Filter Features* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6607.htm>) | Knowledge → Search | Text input, Search button, Enter key | server: `KNOWLEDGE_READ` | `knowledge.ts` | `GET /api/knowledge/search?q=` | Knowledge service |
| Search results | `knowledge-search` | *Working with Find, Search, and Filter Features* (<https://docs.oracle.com/cd/G48897_01/p6help/en/8329.htm>) | After Search | Title, snippet, card type, translation status, score | server; insufficient knowledge is explicit | `knowledge.ts` | `GET /api/knowledge/search` | Knowledge service |
| Published guidance | `knowledge-cards` | `HELP_REFERENCE_PENDING` — CUBI card library; each card links its own official source | Knowledge → Published guidance | Card grid with source title/version and revision | server: published cards only | `knowledge.ts` | `GET /api/knowledge/cards` | Knowledge cards |
| Coverage summary | `knowledge-coverage` | `HELP_REFERENCE_PENDING` — CUBI coverage report | Knowledge → Coverage | Counts by publication status | server | `knowledge.ts` | `GET /api/knowledge/coverage` | Knowledge coverage |
| Coverage sources | `knowledge-coverage` | *About P6 Help* (<https://docs.oracle.com/cd/G48897_01/p6help/en/6602.htm>) | Knowledge → Coverage table | Source, status, mandatory areas, unconverted topics, failures | server | `knowledge.ts` | `GET /api/knowledge/coverage` | Knowledge coverage |
| Organization templates | `knowledge-forms` | `HELP_REFERENCE_PENDING` — shared Form Builder library | Knowledge → Shared Form Builder | Counts, template table | server: form permissions | `knowledge.ts` | `GET /api/forms/organization/overview` | Form Builder |
| Open Form Builder | `knowledge-forms` | `HELP_REFERENCE_PENDING` — existing Engineering surface | Knowledge → button | Link to `/app/`, where the shared editor is mounted | Engineering checks permissions | `knowledge.ts` | none | Engineering app |

---

## Maintenance rules

1. A help URL is added only after it appears in the official TOC response or a
   knowledge card's `source_url` returned by the server.
2. `HELP_REFERENCE_PENDING` is a valid, intentional value. It must not be
   replaced with a guessed topic number.
3. Page titles in this matrix are the exact Enterprise page titles; P6 topic
   titles are the official titles used for the link text.
4. When an API moves from "unverified" to "registered", update both this matrix
   and `ENTERPRISE_API_CONTRACT_STATUS.md`, then re-run the page evidence script.
