# V29 — Executed tests and evidence

- Tested code SHA: `4779f7b4e` (working tree identical for the browser runs).
- Operating environment: Qoder Desktop, local full-stack preview only.
- No Vercel Preview, no deployment, no production database, no production secrets.

## Isolated preview runs

| Suite | Port | Database | Process |
|---|---:|---|---|
| activity-children / conflict / views / visual matrix | 4197 | `.preview/v29-children.sqlite3` (fresh `--reset`) | one preview server, one Chrome per suite; stopped after the run |

No two suites shared a port or a SQLite file. Every E2E stops Chrome and exits 0/1;
the JSON records `testedCodeSha`, timestamps and every assertion result.

## Commands and results

| Command | Result |
|---|---|
| `npx tsc --noEmit` (apps/web) | clean |
| `npm run build` (apps/web) | clean bundle |
| `npm test` (apps/web) | **1186 passed, 0 failed**; `preview-server.test.mjs` **15 passed** |
| `pytest tests/test_p6_activity_children.py tests/test_p6_activity_step_write_api.py tests/test_p6_activity_step_api.py tests/test_p6_activity_step_repository.py tests/test_activity_children_http_routes.py tests/test_p6_activity_step_http_routes.py tests/test_preview_runtime.py tests/test_document_http_routes.py` | **64 passed** |
| `pytest tests/test_project_lifecycle_http_routes.py tests/backend_p0/test_workspace_read_provider.py` | **117 passed** |
| `node e2e/activity-children-v29.mjs` | exit 0 — codes, notebook, steps, document link, Alt sequence |
| `node e2e/activity-conflict-v29.mjs` | exit 0 — two sessions, HTTP 409, winner preserved, fixture restored |
| `node e2e/activity-views-v29.mjs` | exit 0 — network 14 nodes/15 edges, trace, usage profile/spreadsheet |
| `node e2e/visual-matrix-v29.mjs` | exit 0 — 36 cells, 6 distinct theme signatures, RTL verified |

## Browser evidence

- `activity-children.json` + screenshots `01-codes-assigned`, `02-notebook-topic`,
  `03-step-added`, `04-document-linked`, `05-alt-sequence`.
- `conflict-409.json` + `01-winner-saved`, `02-conflict-rejected`.
  Session B's PATCH returned **409**; its editor showed
  `The project service rejected the change: REVISION_CONFLICT`; the reload showed
  session A's value; the fixture name was restored to “Earthworks”.
- `activity-views.json` + `01-network`, `02-trace-logic`, `03-usage-spreadsheet`.
  Usage reported `2 stored period(s)` from a real assignment period created through
  the resource service, not from fabricated rows.
- `visual/visual-matrix.json` + 36 screenshots covering 6 themes × 3 viewport sizes ×
  English LTR / Persian RTL. Graphite and Midnight row contrast ≥ 4.5:1 at every size.

## Not measured here

- The full 4,000+ Python suite was not re-run in this increment; the modules touched by
  this slice plus their neighbours were run as listed above.
- The 73 `verify` rows in `pdf-topic-disposition.md` are not acceptance evidence.
- CI at `6a3bb76a4`: all 10 workflows completed successfully (checked with `gh run list` / `gh run watch`).
