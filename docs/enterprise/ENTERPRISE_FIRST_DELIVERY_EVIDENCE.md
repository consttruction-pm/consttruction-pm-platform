# CUBI Enterprise & Personal Workbench — Delivery Evidence

Status: **second delivery verified** on the real preview runtime (Python WSGI +
SQLite) after merging `main` (PR #2085) and wiring the Enterprise API. Every page
below was reached through the real login path, rendered a real heading, survived
a browser refresh and deep link, and produced no uncaught page error.

- Date: 2026-11-20
- Branch: `feat/cubi-enterprise-workbench` (merge commit `3a405ad` on top of `main` `5bddd3d`)
- Preview base: `http://127.0.0.1:4180`
- Canonical signed-in entry: `/workbench/` (Personal Workbench)
- Enterprise entry: `/cubi/`
- Login path: `/preview/login?next=/cubi/` → persona **Enterprise administrator** (`enterprise`)
- Session after login: `GET /api/session` → **200**, `user_id=preview-enterprise`,
  roles `enterprise_admin`, `project_admin`, tenant `cubi-preview-tenant`
- Browser: headless Chromium via Playwright (`/usr/bin/chromium --no-sandbox`), viewport 1440×1100
- Machine-readable record: [`artifacts/enterprise-preview/evidence.json`](../../artifacts/enterprise-preview/evidence.json)
- Page/field/Help matrix: [`ENTERPRISE_PAGE_FIELD_HELP_MATRIX.md`](ENTERPRISE_PAGE_FIELD_HELP_MATRIX.md)
- API status: [`ENTERPRISE_API_CONTRACT_STATUS.md`](ENTERPRISE_API_CONTRACT_STATUS.md)

## What changed since first delivery

1. The `main` workbench (PR #2085) is the single signed-in entry. `/cubi/workbench`
   and `/cubi/environments` redirect to `/workbench/`; the workbench's Enterprise
   card links to `/cubi/enterprise/dashboard`. No parallel workbench exists.
2. `/api/enterprise/*` is now mounted on the SQLite preview:
   - `EnterpriseTaskHttpMiddleware` over a new `SQLiteEnterpriseTaskRepository`
     (tenant scope, revisions, idempotency, dependency cycle detection, audit);
   - `EnterpriseWorkbenchHttpMiddleware` over `EnterpriseWorkbenchStore`
     (13 record kinds, soft delete/restore, approvals decisions, workflow publish,
     audit, role gates).
3. Enterprise pages now write through real APIs instead of showing a
   not-connected state: dashboard layouts, decisions, teams/invitations/grants,
   tasks, workflows, approvals.
4. Engineering-derived values are never fabricated. Portlet, portfolio indicator,
   trend and EVM routes return `503 ENGINEERING_SOURCE_NOT_CONNECTED`, and the
   client maps that to a dedicated `source_unavailable` state.

## Per-page result (browser pass)

| # | Page | Route | Screenshot | H1 | Refresh + deep link | Write flow exercised |
|---|------|-------|------------|----|---------------------|----------------------|
| 1 | Homepage | `/cubi/` | [01-home.png](../../artifacts/enterprise-preview/01-home.png) | CUBI Platform | pass | — |
| 2 | Login / Auth | `/cubi/login` | [02-login.png](../../artifacts/enterprise-preview/02-login.png) | Sign in | pass | persona login sets `cp_session` |
| 3 | Role & Permission | `/cubi/roles` | [03-roles.png](../../artifacts/enterprise-preview/03-roles.png) | Role & permission selection | pass | — (read-only) |
| 4 | Personal Workbench | `/workbench/` (redirect from `/cubi/workbench`) | [04-workbench.png](../../artifacts/enterprise-preview/04-workbench.png) | Personal Workbench | pass | identity + environment links |
| 5 | Environment Selector | `/workbench/` (redirect from `/cubi/environments`) | [05-environments.png](../../artifacts/enterprise-preview/05-environments.png) | Personal Workbench | pass | — |
| 6 | Enterprise Dashboard | `/cubi/enterprise/dashboard` | [06-dashboard.png](../../artifacts/enterprise-preview/06-dashboard.png) | Enterprise dashboard & portlets | pass | Save layout → server revision shown after reload |
| 7 | Portfolio | `/cubi/enterprise/portfolio` | [07-portfolio.png](../../artifacts/enterprise-preview/07-portfolio.png) | Portfolio & executive center | pass | Record decision → persists after reload |
| 8 | Projects | `/cubi/enterprise/projects` | [08-projects.png](../../artifacts/enterprise-preview/08-projects.png) | Enterprise projects | pass | — (read-only) |
| 9 | Organization & Access | `/cubi/enterprise/access` | [09-access.png](../../artifacts/enterprise-preview/09-access.png) | Organization & access center | pass | Create team → visible after reload |
| 10 | Team & Task Center | `/cubi/enterprise/tasks` | [10-tasks.png](../../artifacts/enterprise-preview/10-tasks.png) | Team & task center | pass | Create task → row appears |
| 11 | Workflow Studio | `/cubi/enterprise/workflows` | [11-workflows.png](../../artifacts/enterprise-preview/11-workflows.png) | Workflow studio | pass | Publish version → register shows v1 |
| 12 | Feedback & Approvals | `/cubi/enterprise/approvals` | [12-approvals.png](../../artifacts/enterprise-preview/12-approvals.png) | Feedback & approval center | pass | Review fills id/revision; decision recorded |
| 13 | Resources & Capacity | `/cubi/enterprise/resources` | [13-resources.png](../../artifacts/enterprise-preview/13-resources.png) | Resources & capacity | pass | — (Engineering read) |
| 14 | Reports & Operations | `/cubi/enterprise/reports` | [14-reports.png](../../artifacts/enterprise-preview/14-reports.png) | Reports & operations | pass | — (existing runtime) |
| 15 | Knowledge & PMBOK | `/cubi/enterprise/knowledge` | [15-knowledge.png](../../artifacts/enterprise-preview/15-knowledge.png) | Knowledge & PMBOK center | pass | — (read-only) |

Browser suite result: **41/41 checks passed** (10 enterprise routes × heading +
refresh/deep link, 2 canonical-entry redirects, 7 write/refresh flows, 1
permission check, page-error/console/network hygiene).

## API verification (same preview, 33 checks)

`/tmp/live_api_check.py` signs in with a real cookie and asserts:

- anonymous `/api/enterprise/teams` → 401 `SESSION_REQUIRED`;
- non-enterprise role → 403 `ENTERPRISE_ACCESS_DENIED`;
- team create 201, idempotent replay returns the same record, key reuse → 409;
- client `tenant_id` → 403 `TENANT_IS_CLIENT_CONTROLLED`;
- patch → revision 2; stale patch → 409; soft delete hides the record → 404;
  restore → revision 4 and visible again;
- task create 201, complete → revision 2, stale patch → 409;
- approval decision 201, status `approved`, duplicate key → 409
  `DUPLICATE_DECISION`, stale revision → 409 `STALE_REVISION`;
- invalid workflow publish → 400 `WORKFLOW_INVALID:step done is unreachable`,
  valid publish → `published_version 1`, stale republish → 409;
- dashboard create/update → revisions 1 and 2;
- audit readable and append-only (POST → 405);
- portlets/portfolio/EVM → 503 `ENGINEERING_SOURCE_NOT_CONNECTED`.

Result: **33/33 passed**.

## Automated tests added

`tests/test_enterprise_workbench_http.py` (19 tests) — real in-memory SQLite store
behind the WSGI middleware: auth, role gates, CRUD/revisions, soft delete and
restore, tenant isolation, client tenant rejection, idempotency, validation,
immutable fields, approval stale/duplicate semantics, workflow graph validation
and versioning, audit, 503 engineering routes, task-route ownership, seed
idempotency.

`tests/test_enterprise_task_sqlite_repository.py` (11 tests) — task persistence:
revision/history, idempotency and key reuse, tenant scoping, personal/project
filters, stale updates, completion actor, dependency cycles and cross-tenant
dependencies, metadata validation, pagination cursor.

Both modules are `unittest`-compatible (pytest is not installed in this sandbox)
and run with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_enterprise_workbench_http.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_enterprise_task_sqlite_repository.py' -v
```

Web side: `npx tsc -p tsconfig.build.json` passes, `npm test` is 1250 + 16 = 1266
passing, `npm run build` produces `dist/web/src/enterprise-entry.bundle.js`.

## Localisation pass

`/tmp/locale_check.js` switched the Enterprise UI through all ten locales
(en, fa, de, zh, ar, fr, ja, ko, ru, tr): **33/33 checks passed**. Each locale keeps
its translated page title, `lang`, and direction (`fa`, `ar` = RTL, others LTR);
Persian dates/digits render through `Intl`; deep links keep RTL; switching back to
English restores LTR. Long-form page copy remains English/Persian with an explicit
English fallback for the other eight locales (see i18n header).

## How to reproduce

```bash
cd /data/repo
CUBI_PREVIEW_ALLOW_LAN=1 PYTHONPATH=src python3 -m construction_pm.preview \
  --web-root apps/web --host 0.0.0.0 --port 4180 --reset
# in another shell:
python3 artifacts/enterprise-preview/verify_api.py
node artifacts/enterprise-preview/verify_browser.js
node artifacts/enterprise-preview/verify_locale.js
node artifacts/enterprise-preview/shoot.js   # refreshes screenshots + evidence.json
```

## Honest gaps at this delivery

- Portlet, portfolio indicator/trend and EVM values are not connected; the API
  returns 503 and the UI says so. No value is derived.
- Task delete, team assignment and Engineering object references are not
  implemented; the task API rejects them.
- Invitation acceptance and dedicated audit/settings pages are not implemented
  (see the ten initial-set pages in the help matrix).
- Dashboard visibility is stored as metadata but not enforced in preview.
- PostgreSQL concurrency (advisory locks, triggers) is **Unverified** here; the
  SQLite adapter is a preview implementation. Production CSRF is also unverified;
  the preview relies on `SameSite=Lax` + HttpOnly cookies.
- Knowledge seed is empty, so cards/search/coverage are legitimately empty.
- Ten initial-set pages (risks, documents, EPS, Team Member activities,
  timesheets, notifications, admin settings, Form Builder page, audit page,
  resource directory) remain MISSING or IN_PROGRESS and are not claimed.
