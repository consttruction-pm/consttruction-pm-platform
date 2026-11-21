# CUBI Enterprise & Personal Workbench — Delivery Evidence

Status: **third delivery verified** on the real preview runtime (Python WSGI +
SQLite). All **25 initial-set pages** are delivered: the 15 pages from the second
delivery plus the 10 remaining pages (risks, documents, EPS, Team Member
activities, timesheets, notifications, admin settings, Form Builder, audit,
directory). Every page was reached through the real login path, rendered a real
heading, survived a browser refresh and deep link, and produced no uncaught page
error.

- Date: 2026-11-21
- Branch: `feat/cubi-enterprise-workbench` (merged to `main` as `e12821b`, PR #2086)
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

## What changed since second delivery

1. The ten remaining initial-set pages are implemented, not stubbed:
   - eight record pages share one config-driven component
     (`apps/web/src/enterprise/pages/records.ts`, specs in `registers.ts`) and
     read/write the generic `/api/enterprise/{kind}` API;
   - Audit (page 24) is a read-only table over `/api/enterprise/audit`;
   - Member Activities (page 19) is a read-only Engineering projection over
     `/api/projects/{id}/p6/activities` with an explicit *Open in Engineering*
     link and no write control.
2. The backend store gained 8 kinds (`risks`, `documents`, `eps`, `timesheets`,
   `notifications`, `settings`, `forms`, `directory`), required-field rules,
   kind-specific validation and an `include_deleted` list filter. `settings` and
   `forms` join the admin-gated kinds.
3. Every new page records a direct official Help topic URL (P6 EPCC TOC) in the
   page header and in the field/Help matrix; CUBI-only concepts are marked
   `HELP_REFERENCE_PENDING`.
4. All ten locales carry translated nav labels and page titles; no locale leaks a
   raw translation key.

## Per-page result (browser pass)

All 25 routes were loaded from the real preview over `cp_session`. For each page
the suite asserts one visible `<h1>`, no uncaught page error, no console error and
no failed same-origin request.

| # | Page | Route | Screenshot | Write flow exercised |
|---|------|-------|------------|----------------------|
| 1 | Homepage | `/cubi/` | [01-home.png](../../artifacts/enterprise-preview/01-home.png) | — |
| 2 | Login / Auth | `/cubi/login` | [02-login.png](../../artifacts/enterprise-preview/02-login.png) | persona login sets `cp_session` |
| 3 | Role & Permission | `/cubi/roles` | [03-roles.png](../../artifacts/enterprise-preview/03-roles.png) | read-only |
| 4 | Personal Workbench | `/workbench/` (redirect from `/cubi/workbench`) | [04-workbench.png](../../artifacts/enterprise-preview/04-workbench.png) | identity + environment links |
| 5 | Environment Selector | `/workbench/` (redirect from `/cubi/environments`) | [05-environments.png](../../artifacts/enterprise-preview/05-environments.png) | redirect only |
| 6 | Enterprise Dashboard | `/cubi/enterprise/dashboard` | [06-dashboard.png](../../artifacts/enterprise-preview/06-dashboard.png) | Save layout → server revision after reload |
| 7 | Portfolio | `/cubi/enterprise/portfolio` | [07-portfolio.png](../../artifacts/enterprise-preview/07-portfolio.png) | Record decision → persists |
| 8 | Projects | `/cubi/enterprise/projects` | [08-projects.png](../../artifacts/enterprise-preview/08-projects.png) | read-only |
| 9 | Organization & Access | `/cubi/enterprise/access` | [09-access.png](../../artifacts/enterprise-preview/09-access.png) | Create team → visible after reload |
| 10 | Team & Task Center | `/cubi/enterprise/tasks` | [10-tasks.png](../../artifacts/enterprise-preview/10-tasks.png) | Create task → row appears |
| 11 | Workflow Studio | `/cubi/enterprise/workflows` | [11-workflows.png](../../artifacts/enterprise-preview/11-workflows.png) | Publish version → v1 |
| 12 | Feedback & Approvals | `/cubi/enterprise/approvals` | [12-approvals.png](../../artifacts/enterprise-preview/12-approvals.png) | Decision recorded |
| 13 | Resources & Capacity | `/cubi/enterprise/resources` | [13-resources.png](../../artifacts/enterprise-preview/13-resources.png) | Engineering read |
| 14 | Reports & Operations | `/cubi/enterprise/reports` | [14-reports.png](../../artifacts/enterprise-preview/14-reports.png) | existing runtime |
| 15 | Knowledge & PMBOK | `/cubi/enterprise/knowledge` | [15-knowledge.png](../../artifacts/enterprise-preview/15-knowledge.png) | read-only |
| 16 | Risks & Issues | `/cubi/enterprise/risks` | [16-risks.png](../../artifacts/enterprise-preview/16-risks.png) | Create risk → server row; edit/delete/restore |
| 17 | Documents | `/cubi/enterprise/documents` | [17-documents.png](../../artifacts/enterprise-preview/17-documents.png) | Create document metadata → CRUD |
| 18 | EPS Structure | `/cubi/enterprise/eps` | [18-eps.png](../../artifacts/enterprise-preview/18-eps.png) | Create EPS node → CRUD |
| 19 | Member Activities | `/cubi/enterprise/member-activities` | [19-member-activities.png](../../artifacts/enterprise-preview/19-member-activities.png) | **read-only** Engineering projection |
| 20 | Timesheets | `/cubi/enterprise/timesheets` | [20-timesheets.png](../../artifacts/enterprise-preview/20-timesheets.png) | Create hours entry → CRUD, hours/date validated |
| 21 | Notifications | `/cubi/enterprise/notifications` | [21-notifications.png](../../artifacts/enterprise-preview/21-notifications.png) | Create notification → CRUD |
| 22 | Admin Settings | `/cubi/enterprise/settings` | [22-settings.png](../../artifacts/enterprise-preview/22-settings.png) | Admin-gated key/value CRUD |
| 23 | Form Builder | `/cubi/enterprise/forms` | [23-forms.png](../../artifacts/enterprise-preview/23-forms.png) | Admin-gated form schema CRUD |
| 24 | Audit Log | `/cubi/enterprise/audit` | [24-audit.png](../../artifacts/enterprise-preview/24-audit.png) | **read-only**; POST → 405 |
| 25 | Directory | `/cubi/enterprise/directory` | [25-directory.png](../../artifacts/enterprise-preview/25-directory.png) | Create contact → CRUD |

Browser suite result: **65/65 checks passed** (25 routes × heading + refresh/deep
link, 2 canonical-entry redirects, write/refresh flows, permission checks,
read-only assertions for pages 19 and 24, page-error/console/network hygiene).

## API verification (same preview, 49 checks)

`artifacts/enterprise-preview/verify_api.py` signs in with a real cookie and
asserts, for the new kinds: create → list → patch (revision+1) → soft delete →
`include_deleted` visibility → restore; cross-tenant 404; viewer write 403
`ENTERPRISE_WRITE_DENIED`; admin kinds (settings/forms) readable but write 403
`ENTERPRISE_ADMIN_REQUIRED`; timesheet hours/date validation
(`HOURS_INVALID`, `WORK_DATE_INVALID`); risk type/severity validation; form field
schema validation (`FORM_FIELDS_REQUIRED`, `FORM_FIELD_INVALID`); audit append-only
and viewer audit 403 `ENTERPRISE_ACCESS_DENIED`.

It also re-asserts the earlier contract: anonymous 401, tenant override 403,
idempotent replay, stale revision 409, approval duplicate-key 409, workflow graph
validation and publish versioning, dashboard revisions, and the
`503 ENGINEERING_SOURCE_NOT_CONNECTED` answers for portlets/portfolio/EVM.

Result: **49/49 passed**; the script is rerun-safe (time-based idempotency keys).

## Automated tests

`tests/test_enterprise_workbench_http.py` — **26 tests** (was 19): the 7 added
tests cover full CRUD + restore for the eight new kinds, `include_deleted`,
tenant isolation for a second tenant, timesheet hours/date rules on create and
PATCH, risk type/severity rules, form schema errors, admin-gated kinds
(`403 ENTERPRISE_ADMIN_REQUIRED` on write, readable on GET) and viewer write
denial.

`tests/test_enterprise_task_sqlite_repository.py` — 11 tests (unchanged).

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_enterprise_workbench_http.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_enterprise_task_sqlite_repository.py' -v
```

Web side: `npx tsc -p tsconfig.build.json` passes, `npm test` is **1251 + 16**
passing (including the new assertion that every initial-set page is titled in all
ten locales without leaking a raw key), and `npm run build` produces
`dist/web/src/enterprise-entry.bundle.js`.

## Localisation pass

`artifacts/enterprise-preview/verify_locale.js` switched the Enterprise UI through
all ten locales (en, fa, de, zh, ar, fr, ja, ko, ru, tr) and additionally checked
the Risks page title in each locale: **43/43 checks passed**. Each locale keeps
its translated title, `lang`, and direction (`fa`, `ar` = RTL, others LTR);
Persian dates/digits render through `Intl`; switching back to English restores
LTR. Long-form page copy remains English/Persian with an English fallback for the
other eight locales (see i18n header).

## How to reproduce

```bash
cd /data/repo
PYTHONPATH=src python3 -m construction_pm.preview \
  --web-root apps/web --host 127.0.0.1 --port 4180 --reset
# in another shell:
python3 artifacts/enterprise-preview/verify_api.py
CUBI_CHROME_NO_SANDBOX=1 node artifacts/enterprise-preview/verify_browser.js
node artifacts/enterprise-preview/verify_locale.js
CUBI_CHROME_NO_SANDBOX=1 node artifacts/enterprise-preview/shoot.js   # screenshots + evidence.json
```

## Honest gaps at this delivery

- Portlet, portfolio indicator/trend and EVM values are not connected; the API
  returns 503 and the UI says so. No value is derived.
- Task delete, team assignment and Engineering object references are not
  implemented; the task API rejects them.
- Member Activities is read-only. It projects Engineering activities and links
  out; it does not create, edit or delete activities.
- `eps` is an Enterprise-side structure only; it does not mutate the
  authoritative Engineering EPS.
- `settings` stores tenant key/value data; nothing consumes a key yet, and no page
  claims a behaviour change.
- `forms` validates the field schema only; publishing/submission storage is out of
  scope for this delivery.
- Invitation acceptance is not implemented; the access page marks that row
  *pending server route*.
- Dashboard visibility is stored as metadata but not enforced in preview.
- PostgreSQL concurrency (advisory locks, triggers) is **Unverified** here; the
  SQLite adapter is a preview implementation. Production CSRF is also unverified;
  the preview relies on `SameSite=Lax` + HttpOnly cookies.
- Knowledge seed is empty, so cards/search/coverage are legitimately empty.
- CUBI-only fields without an official P6/EPPM topic are marked
  `HELP_REFERENCE_PENDING`; the Help link points at the closest official topic
  only when one exists.
