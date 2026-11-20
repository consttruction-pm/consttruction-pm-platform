# CUBI Enterprise & Personal Workbench — First Delivery Evidence

Status: **first delivery verified** on the real preview runtime (Python WSGI + SQLite).
Every page below was reached through the real login path, rendered a real heading,
survived a browser refresh, and produced no uncaught page error.

- Date: 2026-11-20
- Preview base: `http://127.0.0.1:4180`
- Entry route: `/cubi/`
- Login path: `/preview/login?next=/cubi/` → persona **Enterprise administrator** (`enterprise`)
- Session after login: `GET /api/session` → **200**, `user_id=preview-enterprise`,
  roles `enterprise_admin`, `project_admin`, tenant `cubi-preview-tenant`
- Browser: headless Chromium via Playwright (`/usr/bin/chromium --no-sandbox`), viewport 1440×1000
- Machine-readable record: [`artifacts/enterprise-preview/evidence.json`](../../artifacts/enterprise-preview/evidence.json)

## Per-page result

| # | Page | Route | Screenshot | HTTP | Access | H1 | Refresh | Browser test | API status |
|---|------|-------|------------|------|--------|----|---------|--------------|------------|
| 1 | Homepage | `/cubi/` | [01-home.png](../../artifacts/enterprise-preview/01-home.png) | 200 | signed in | CUBI Platform | 1× h1 | pass, 0 page errors | 2 calls, 0 fail |
| 2 | Login / Auth (P6 About Security) | `/cubi/login` | [02-login.png](../../artifacts/enterprise-preview/02-login.png) | 200 | signed in | Sign in | 1× h1 | pass, 0 page errors | 2 calls, 0 fail |
| 3 | Role & Permission Selection | `/cubi/roles` | [03-roles.png](../../artifacts/enterprise-preview/03-roles.png) | 200 | signed in | Role & permission selection | 1× h1 | pass, 0 page errors | 2 calls, 0 fail |
| 4 | Personal Workbench Dashboard | `/cubi/workbench` | [04-workbench.png](../../artifacts/enterprise-preview/04-workbench.png) | 200 | signed in | Personal workbench | 1× h1 | pass, 0 page errors | 6 calls, 4 honest 404 probes |
| 5 | Environment Selector | `/cubi/environments` | [05-environments.png](../../artifacts/enterprise-preview/05-environments.png) | 200 | signed in | Choose an environment | 1× h1 | pass, 0 page errors | 2 calls, 0 fail |
| 6 | Enterprise Dashboard & Portlets | `/cubi/enterprise/dashboard` | [06-dashboard.png](../../artifacts/enterprise-preview/06-dashboard.png) | 200 | signed in | Enterprise dashboard & portlets | 1× h1 | pass, 0 page errors | 8 calls, 5 honest 404 probes |
| 7 | Portfolio & Executive Center | `/cubi/enterprise/portfolio` | [07-portfolio.png](../../artifacts/enterprise-preview/07-portfolio.png) | 200 | signed in | Portfolio & executive center | 1× h1 | pass, 0 page errors | 6 calls, 4 honest 404 probes |
| 8 | Enterprise Projects / Project Portal | `/cubi/enterprise/projects` | [08-projects.png](../../artifacts/enterprise-preview/08-projects.png) | 200 | signed in | Enterprise projects | 1× h1 | pass, 0 page errors | 2 calls, 0 fail |
| 9 | Organization & Access Center | `/cubi/enterprise/access` | [09-access.png](../../artifacts/enterprise-preview/09-access.png) | 200 | signed in | Organization & access center | 1× h1 | pass, 0 page errors | 10 calls, 8 honest 404 probes |
| 10 | Team & Task Center | `/cubi/enterprise/tasks` | [10-tasks.png](../../artifacts/enterprise-preview/10-tasks.png) | 200 | signed in | Team & task center | 1× h1 | pass, 0 page errors | 3 calls, 1 honest 404 probe |
| 11 | Workflow Studio | `/cubi/enterprise/workflows` | [11-workflows.png](../../artifacts/enterprise-preview/11-workflows.png) | 200 | signed in | Workflow studio | 1× h1 | pass, 0 page errors | 3 calls, 1 honest 404 probe |
| 12 | Feedback & Approval Center | `/cubi/enterprise/approvals` | [12-approvals.png](../../artifacts/enterprise-preview/12-approvals.png) | 200 | signed in | Feedback & approval center | 1× h1 | pass, 0 page errors | 4 calls, 2 honest 404 probes |
| 13 | Resources & Capacity | `/cubi/enterprise/resources` | [13-resources.png](../../artifacts/enterprise-preview/13-resources.png) | 200 | signed in | Resources & capacity | 1× h1 | pass, 0 page errors | 6 calls, 0 fail |
| 14 | Reports & Operations | `/cubi/enterprise/reports` | [14-reports.png](../../artifacts/enterprise-preview/14-reports.png) | 200 | signed in | Reports & operations | 1× h1 | pass, 0 page errors | 6 calls, 0 fail |
| 15 | Knowledge & PMBOK Center | `/cubi/enterprise/knowledge` | [15-knowledge.png](../../artifacts/enterprise-preview/15-knowledge.png) | 200 | signed in | Knowledge & PMBOK center | 1× h1 | pass, 0 page errors | 8 calls, 0 fail |

All 15 pages returned HTTP 200, kept exactly one `h1` after a full reload, and raised
zero uncaught page errors.

## API capability matrix (same session)

Registered and answering on the preview runtime:

| Method | Route | Status |
|--------|-------|--------|
| GET | `/api/session` | 200 |
| GET | `/api/projects` | 200 |
| GET | `/api/projects/{id}/p6/resources` | 200 |
| GET | `/api/projects/{id}/p6/resource-capacities` | 200 |
| GET | `/api/projects/{id}/documents` | 200 |
| GET | `/api/projects/{id}/risks` | 200 |
| GET | `/api/projects/{id}/p6/issues` | 200 |
| GET | `/api/projects/{id}/reports/catalogue` | 200 |
| GET | `/api/projects/{id}/reports` | 200 |
| GET | `/api/knowledge/cards` | 200 (empty seed) |
| GET | `/api/knowledge/coverage` | 200 |
| GET | `/api/knowledge/search?q=baseline` | 200 (empty result) |
| GET | `/api/forms/organization/overview` | 200 |

Contract defined but **route not registered on this preview**, reported as Unverified
(CUBI renders a not-connected state, never mock data or fake success):

| Method | Route | Status |
|--------|-------|--------|
| GET | `/api/enterprise/tasks` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/dashboards` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/organizations` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/approvals` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/portfolios` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/decisions` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/workflows` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/feedback` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/portfolio/indicators` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/enterprise/portfolio/trends` | 404 `ROUTE_NOT_FOUND` |
| GET | `/api/v1/schedule/projects/{id}/jobs/{job_id}` | 404 for unknown id |

The console `Failed to load resource: 404` entries in the capture are exactly these
honest probes. They are not silent failures: each is surfaced in the page as an
unavailable capability with its route shown.

## Behaviour verified beyond screenshots

- **Login path is real.** Pages are only reached after `POST` to `/preview/login`
  with the `enterprise` persona; the response sets the `cp_session` cookie and
  redirects to `/cubi/` (303 → `/cubi/`). Unauthenticated requests are not silently
  rendered as signed-in.
- **Layout persistence is real.** Dashboard: 6 portlets → add one from the catalog →
  save → reload → 7 portlets, read back from device-local storage.
- **RTL and locale switching work.** Setting locale `fa` yields `dir="rtl"`,
  `lang="fa"`, and a Persian heading; 10 locales are wired with English fallback.
- **Read-only Engineering projection.** Resources & capacity renders the raw
  `capacity`/`scope` payload (`max_units`, `unit_basis`, `hours_per_time_period`,
  `project_revision`) with no aggregation or recalculation.
- **Reports reuse the existing runtime.** Catalogue and definitions come from the
  real reporting routes; no parallel queue or worker is created.

## How to reproduce

```bash
cd /data/repo
CUBI_PREVIEW_ALLOW_LAN=1 PYTHONPATH=src python3 -m construction_pm.preview \
  --web-root apps/web --host 0.0.0.0 --port 4180 --reset
# in another shell:
python3 /tmp/shoot.py   # writes artifacts/enterprise-preview/*.png and the JSON record
```

## Honest gaps at first delivery

- `/api/enterprise/*` domain routes are defined in the contract document but not yet
  registered on the SQLite preview; those pages show an explicit unavailable state.
- The PostgreSQL-backed task/dashboard persistence (advisory locks, triggers) cannot
  run on the SQLite preview and is therefore **Unverified**, not claimed working.
- Long-form localization is reviewed for `en` and `fa` only; the other eight locales
  ship interface strings with English fallback.
- The Knowledge store seed is empty, so cards list is empty and coverage is zero;
  the routes and UI are proven, the content is not.
