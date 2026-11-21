# CUBI — page acceptance report

**Audited SHA:** `0014928bf` (this work adds `/workbench/` and the matrix documents on top)
**Date:** 2026-11-20
**Matrix:** `CUBI_MASTER_PAGE_COMPONENT_MATRIX.csv` / `.json` — 86 rows (25 initial + 61 remaining)
**Rule applied:** a page is `VERIFIED` only with an observed browser proof; a route alone is never acceptance.

> **V26 re-audit (2026-11-21, supersedes the Enterprise rows below).**
> Branch `feat/cubi-entry-enterprise-operational` (PR #2089) on `main`
> `b2b20793c`. All 20 Enterprise data routes are now served under `/cubi/*` by
> `enterprise.html` and were opened by direct URL and hard refresh in the shared
> preview (port 4191; 4180 was occupied by an unrelated stale server). The
> persona matrix, controls, localization and limits are recorded in
> `docs/enterprise/ENTERPRISE_V26_ENTRY_ROUTING_AND_OPERATIONS.md` with
> artefacts in `artifacts/enterprise-preview/v26/`. Rows 16–25 below reflect the
> older `/enterprise/` audit and must not be read as current Enterprise status.


## 1. Test evidence collected at this SHA

| Gate | Result |
|---|---|
| Python suite with PostgreSQL (`CONSTRUCTION_PM_POSTGRES_DSN` + `P6_TEST_POSTGRES_DSN`) | 5382 passed, 1 skipped (`pmcontrols` not installed) |
| Production web app + preview runtime tests | 53 passed |
| Web unit tests | 1239 passed → **1244** after the workbench suite (5 new) |
| Preview server tests | 15 passed → **16** (new `/workbench/` resolver case) |
| Web typecheck + build | clean (tsc, esbuild) |
| Browser E2E (workspace, real runtime) | 101 checks, 55 screenshots |
| Public-site responsive audit | 18/18 |
| Pages artifact validation | 252 documents, canonicals, 10 locale alternates |
| Capability matrix regeneration | no diff (C01–C35) |
| Help topic URLs | sampled topics return HTTP 200 (`using_main_windows.htm`, `the_gantt_chart.htm`, EPPM `6608.htm`, `50904.htm`, `6660.htm`) |

## 2. Entry-flow evidence (new in this revision)

Run against the production WSGI stack with PostgreSQL and a seeded owner:

```
GET /workbench/               → 302 Location: /login?next=/workbench/     (server gate)
POST /api/session             → 200 {roles:[enterprise_admin,project_admin], tenant:cubi-e2e-tenant}
GET /workbench/ (with cookie) → 200 app shell (main.bundle.js referenced)
GET /api/projects             → 200 {"projects":[{project_id:cubi-e2e-project,...}]}
GET /api/enterprise/tasks     → 200
```

Unit evidence (`apps/web/src/personal-workbench.test.ts`): ten locales complete and translated, locale normalization (`fa-IR`, `tr-TR`, `zh-Hans-CN`), RTL only for fa/ar, grant logic driven by server signals, environment links limited to `/app?view=live` and `/enterprise/`, locale-aware dates and numbers (Persian digits asserted).

Not yet captured: a browser screenshot of `/workbench/`. It is listed as an open item, not as done.

## 3. Acceptance by page (initial 25)

| # | Page | Route | Status | Browser proof |
|---|---|---|---|---|
| 1 | Public homepage | `/` | VERIFIED | responsive audit |
| 2 | Login / entry | `/login` | VERIFIED | production-login E2E |
| 3 | Role / working context | `/workbench/` | WIRED_READ | — |
| 4 | Personal workbench | `/workbench/` | WIRED_READ | — |
| 5 | Environment selector | `/workbench/` + `/environments/` | WIRED_READ | — |
| 6 | Engineering shell | `/app` | VERIFIED | preview E2E |
| 7 | Projects / EPS | `/app/projects/` | WIRED_WRITE | preview E2E (register) |
| 8 | WBS | `/app/wbs/` | VERIFIED | preview E2E |
| 9 | Activities | `/app/activities/` | VERIFIED | preview E2E |
| 10 | Activity details | `/app/activities/` | VERIFIED | preview E2E |
| 11 | Relationships / network | `/app/activities/` | VERIFIED | preview E2E |
| 12 | Gantt | `/app/activities/` | VERIFIED | preview E2E |
| 13 | Resources / assignments | `/app/resources/` | WIRED_WRITE | — |
| 14 | Calendars | `/app/calendars/` | WIRED_WRITE | — |
| 15 | Reports / tracking | `/app/reports/`, `/app/tracking/` | WIRED_READ | — |
| 16 | Enterprise dashboard | `/enterprise/` | MISSING | — |
| 17 | Portfolio / executive | `/enterprise/portfolio/` | MISSING | — |
| 18 | Enterprise projects | `/enterprise/projects/` | MISSING | — |
| 19 | Organization & access | `/enterprise/organization/` | MISSING | — |
| 20 | Team & task center | `/enterprise/` | WIRED_WRITE | E2E task flows (unit + API) |
| 21 | Workflow studio | `/enterprise/workflows/` | MISSING | — |
| 22 | Approval center | `/enterprise/approvals/` | MISSING | — |
| 23 | Resources & capacity | `/enterprise/resources/` | MISSING | — |
| 24 | Operations & reports | `/enterprise/operations/` | MISSING | — |
| 25 | Project portal / documents | `/enterprise/portal/` | MISSING | — |

Summary: 8 VERIFIED, 4 WIRED_WRITE, 4 WIRED_READ, 9 MISSING. The initial 25-page delivery is **not complete**; the nine missing Enterprise surfaces are the blocking gap (see `CUBI_INTEGRATION_BLOCKERS.md` B1–B5).

## 4. Status of the remaining register

- **Engineering:** 67 rows — 27 VERIFIED (browser), 16 WIRED_WRITE, 24 WIRED_READ, 0 MISSING pages; field-level audit complete for project creation only.
- **Enterprise:** 16 rows — 1 WIRED_WRITE (`/enterprise/`), 1 WIRED_READ (`/environments/`), 14 MISSING (no route).

## 5. What was changed in this revision

- `apps/web/src/personal-workbench.ts` + test: real signed-in workbench, ten locales, grant-driven environment selection.
- `/workbench/` route in the client, the preview server and the production WSGI gate.
- `/login` default target now `/workbench/`; Enterprise back link points to `/workbench/`.
- Workbench styles in both stylesheets (identical), editor CSS already mirrored.
- Matrices, plan, contract, blockers and this report.

No Scheduling Core, Activities, or Enterprise backend file was modified.
