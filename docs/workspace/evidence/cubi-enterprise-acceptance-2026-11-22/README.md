# CUBI Enterprise environment acceptance — 2026-11-22

## What changed

The Enterprise environment had never been driven end to end in the browser.
This slice adds a real journey to `apps/web/e2e/preview-e2e.mjs` and fixes the
two product defects it exposed.

| Layer | File | Change |
| --- | --- | --- |
| Enterprise sign-in | `apps/web/src/enterprise/pages/login.ts` | preview sign-in renders persona buttons posting to the server-declared `cubi-login-path`, not a credential form posting to `/api/session` |
| Runtime validation | `src/construction_pm/enterprise_workbench_http.py` | a blank optional `email` from a record form is "not provided", not `EMAIL_INVALID` |
| Browser journey | `apps/web/e2e/preview-e2e.mjs` | Enterprise persona, own document, registers, real writes, audit, RTL, server gate |
| Tests | `tests/test_enterprise_workbench_http.py` | blank email accepted, malformed address still rejected |

## Defects found and fixed

1. **Preview sign-in posted to an unimplemented route.** The Enterprise login
   page always rendered the production credential form, whose submit targets
   `POST /api/session`. The preview server has no password directory and only
   implements `POST /preview/login`, so every Enterprise sign-in in the preview
   failed. The page now reads the server-declared login path and offers the same
   demo persona grid the Engineering shell already uses. Enterprise
   entitlements are still checked server-side after the redirect.
2. **A record with an optional email could not be created.** The register form
   submits untouched optional text fields as `""`, and the server's email check
   rejected the empty string with `400 EMAIL_INVALID`. A blank email is now
   treated as absent; a malformed non-empty address is still rejected.

## Journey coverage

The journey uses the Enterprise persona and the same real SQLite stores:

- Personal Workbench shows the identity, both environment cards, both
  authorized projects and no restricted note;
- the Enterprise dashboard is its own document (no `#app`, `cubi-body`), with
  the full sidebar, zero `/enterprise` links and a `/workbench/` return link;
- access registers read the seeded tenant store;
- a task is created through the Task API form, read back from
  `/api/enterprise/tasks?limit=100` and survives a full reload;
- the knowledge centre states its real published state;
- a directory record is created through the form, listed back from
  `EnterpriseWorkbenchStore` and found in the append-only audit trail;
- Persian keeps the Enterprise document and flips direction;
- a planner session is returned by the server gate to the Personal Workbench
  with the restricted note and no Enterprise link.

Portfolio portlets answer `503 ENGINEERING_SOURCE_NOT_CONNECTED` while the
Engineering source is not connected. The browser check now tolerates exactly
that code on `/api/enterprise/{portlets,portfolio,evm}` and still fails every
other 5xx. This is the product's documented honest state; the dashboard renders
it instead of inventing numbers.

## Verification

- `python -m pytest tests/test_enterprise_workbench_http.py -q` — 26 passed
- `npm run typecheck` — clean
- `npm test` — 1296 + 16 passed
- `CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` — 127 recorded checks:
  - `Enterprise preview sign-in uses the declared demo endpoint, not a failing credential form`
  - `Personal Workbench offers the two environments and starts no workspace itself`
  - `Enterprise dashboard is its own document with the full sidebar`
  - `Enterprise access registers read the seeded tenant store`
  - `Enterprise task write persists and is readable through the canonical API`
  - `Enterprise knowledge center states its real published state`
  - `Enterprise directory write is read back from the workbench store`
  - `Enterprise audit lists the recorded write`
  - `Enterprise locale switch keeps its own document and direction`
  - `Enterprise returns to the shared Personal Workbench, not Engineering`
  - `server gate returns a non-Enterprise session to the Personal Workbench with the reason`
  - `no uncaught browser exceptions or unexpected API 5xx responses`
    (`engineering_source_not_connected_503: 3`)

Screenshot: `apps/web/e2e/artifacts/enterprise-dashboard.png`.

## Not claimed

No PostgreSQL deployment was exercised here: the run uses the preview
runtime's SQLite stores. The Enterprise source-connected portfolio/EVM portlets
remain unproven until an Engineering source is connected and
`CONSTRUCTION_PM_DATABASE_URL`, `CONSTRUCTION_PM_SESSION_SECRET` and
`CONSTRUCTION_PM_PUBLIC_ORIGIN` are configured in the real deployment.
