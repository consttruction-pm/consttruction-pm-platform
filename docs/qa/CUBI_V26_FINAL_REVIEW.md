# CUBI Version 26 — final review, regression and blocker report

Date: 2026-11-12
Repository: `consttruction-pm/consttruction-pm-platform`
Reviewed branch: `main` @ `66e106a` (Stage G merged as `85e24df`; docs record merged as `66e106a`)

This report closes the Version 26 workspace programme. It records what shipped, the regression
evidence gathered on the final `main`, the cross-cutting invariants that were re-checked, and every
remaining blocker or honest gap. Per-stage detail lives in
[`CUBI_V26_EXECUTION_CHECKPOINT.md`](CUBI_V26_EXECUTION_CHECKPOINT.md); window-level status lives in
[`v26-window-traceability-and-acceptance-matrix.md`](../workspace/architecture/v26-window-traceability-and-acceptance-matrix.md)
and [`WEB_SURFACE_TRACEABILITY_MATRIX.md`](../engineering/WEB_SURFACE_TRACEABILITY_MATRIX.md).

## 1. Scope reviewed

Every Version 26 workspace module from the source register, delivered in order: central shell and
Activities layout (A/B), Projects window and details (C), resources, assignments, roles and calendars
(D), the project registers (E), the Administration/Utilities block (F), and canonical workspace
integration (G). The review covers the shared Python core, the versioned HTTP contracts, the WSGI
preview/production composition, the TypeScript workspace surfaces, and the browser journey through
the real preview runtime.

## 2. Stage completion

| Stage | Delivery | Merge |
| --- | --- | --- |
| A | Central shell: eight menus, toolbar families, icon registry, shortcut registry | `e3ce8ef8` (#1737) |
| B | Activities Show on Top / Show on Bottom, Trace Logic | `b241699b` |
| C | Projects window and Project Details | `cb9cc002` |
| D1 | Resource read register and calendar verification | `4d0b5783` |
| D1b | Activities Classic Schedule Layout selector | `71ca85cf` |
| D2a | Authoritative resource master, hierarchy, revision-guarded editor | `9cfd4813` |
| D2b | Assignment grouping, spreadsheet, profile and revise workflow | `f959a7dc` |
| D2c | Role hierarchy, proficiency, effective-dated rates and limits | `a9cdc362` |
| D3a | Calendar create-from-base, workweek/split shifts, exception removal | `03d61a39` |
| D3b | Jalali calendar system and revision-guarded exception editing | `1ba5c9ef` |
| D3c | Calendar usage references and assignment calendar selection | `cef505e9` (#1769) |
| E1 | Project issue register, status graph and history | `c920dc19` (#1757) |
| E2 | Document register, audited status graph and history | `8f9b37a0` (#1759) |
| E3 | Budget register, pending changes, funding sources | `9c11331b` (#1761) |
| E3b | Expense and cost-account register | `67b69adb` (#1763) |
| E4 | Threshold register, monitoring runs, generated issues | `a761b5be` (#1765) |
| E5 | Risk register, scoring matrix, response history | `1342b60a` (#1767) |
| F1 | Report register, stored runs, report window | `09022f87` (#1771) |
| F2 | Administration preferences, dictionaries, permission matrix | `0337a7ad` (#1773) |
| F3 | CSV import/export with validated resource writes | `20f49d5b` (#1775) |
| F4 | Project and layout backup/recovery | `90863b3` (#1777) |
| G | Canonical menu-bar integration for every F-stage window | `85e24df` (#1779) |

## 3. Final regression evidence (on `main` @ `66e106a`)

| Check | Command | Result |
| --- | --- | --- |
| Python suite | `PYTHONPATH=src python -m pytest tests -q` | **3512 passed, 109 skipped**, 0 failed |
| Web type check | `cd apps/web && npx tsc --noEmit` | clean |
| Web unit/integration | `cd apps/web && npm test` | **863** `tsx` tests + **14** `node --test` tests pass, 0 failed |
| Web bundle | `cd apps/web && npm run build` | `main`, `global-assistant-launcher` and `landing-entry` bundles written |
| Browser E2E — Reports | `node e2e/reports-v26.mjs` | 9/9 scenarios |
| Browser E2E — Administration | `node e2e/administration-v26.mjs` | 9/9 scenarios |
| Browser E2E — Import / Export | `node e2e/exchange-v26.mjs` | 8/8 scenarios |
| Browser E2E — Backup / Recovery | `node e2e/backup-v26.mjs` | 7/7 scenarios |
| Browser E2E — Canonical menu bar | `node e2e/workspace-canonical-v26.mjs` | 7/7 scenarios |
| Post-merge CI (Stage G) | `gh run list --branch main` on `85e24df` | 5/5 workflows success |
| Post-merge CI (Stage G docs) | same, on `66e106a` | 3/3 triggered workflows success (docs-only paths skip Web/Pages) |

All five browser suites ran against one freshly reset preview runtime
(`PYTHONPATH=src python -m construction_pm.preview --host 127.0.0.1 --port 4193 --reset`), logged in
through the preview personas, and reported zero browser exceptions, zero console errors and zero
API 5xx responses.

## 4. Cross-cutting invariants re-checked

- **Multi-tenant and project isolation** — every versioned contract resolves the tenant/project from
  `BackendScope` and rejects cross-scope access with `CROSS_SCOPE_ACCESS`; tests across the E and F
  suites assert the 403/409 paths.
- **Optimistic locking** — every mutable register writes under `expected_revision` and returns a typed
  conflict (`*_REVISION_CONFLICT`) plus the authoritative record; a stale browser never overwrites.
- **Idempotency** — capture, import, restore and register creates require a key; replays return the
  stored result and key reuse with different content returns 409.
- **Jalali and Gregorian dates** — calendar exceptions, progress and financial periods accept both
  systems; the Jalali conversion is covered by the D3b suite and its browser evidence.
- **Time zones and work time** — calendar snapshots, split shifts and non-overlapping shift
  validation remain the single source of working time; schedule results stay in the shared core.
- **RTL/LTR** — every new surface has a Persian right-to-left browser capture at 1280×720; the
  Stage G suite also verifies the menu bar itself in RTL.
- **Eight locales** — the locale registry still offers eight languages; authored strings are English
  and Persian, and missing-pack coverage stays an explicit audit gap (GAP-I18N-01).
- **Single shared calculation core** — no surface re-implements CPM, calendars or money math; the
  E/F/G windows read and write through the existing repositories and contract APIs.
- **CUBI identity** — no Oracle/Primavera/P6 product name appears in the workspace chrome or the new
  surfaces; browser assertions enforce this.
- **Issue #1722** was not modified at any point in this programme.

## 5. Remaining blockers and honest gaps

Blocking items (a named external dependency or a server capability is required):

| ID | Class | Gap | Why it blocks |
| --- | --- | --- | --- |
| GAP-V26-01 | Evidence | No licensed Version 26 reference run exists in this environment | Numeric parity cannot be claimed; no row can be `IMPLEMENTED_AND_PARITY_TESTED` until an authorized dataset is available |

Resolved on branch `feat/agent3-core-docs-tracking-storage` (not merged to `main`):

| ID | Delivery | Evidence |
| --- | --- | --- |
| GAP-DOC-02 | Binary document upload/download with an allow-listed MIME check, SHA-256 integrity, content-addressed `LocalDocumentStorage`, append-only `project_document_content` versions and idempotent uploads. Routes: `POST/GET .../documents/{id}/content`, `.../content/{version}`, `.../content/versions`; 413/415/409 mappings; WSGI `CONTENT_TYPE` propagation. | `document_storage.py`, `document_content_repository.py`, `document_application.py`, `tests/test_document_binary_storage.py`, preview round-trip in `tests/test_preview_documents.py` |
| GAP-TRK-01 | Authoritative tracking read model backed by the published schedule facts provider: project table rows, bar-chart buckets, start profile, exact-Decimal resource aggregates and WBS groups, served by `GET /api/projects/{project}/tracking/read` (`tracking-read-model.v1`); the Web Tracking window is wired to the contract with per-view controls, strict payload verification and honest loading/empty/error states | `tracking_read_model.py`, `tests/test_tracking_read_model.py`, `apps/web/src/workspace-tracking.ts`, `apps/web/src/workspace-tracking.test.ts`, `tests/test_project_lifecycle_wsgi.py`, `apps/web/e2e/tracking-v26.mjs` |
| GAP-RPT-03 | Report-run export pipeline over the stored immutable snapshot: CSV (UTF-8 BOM) and typed XLSX through `GET .../reports/{report_id}/runs/{run_id}/export?format=csv\|xlsx` | `report_export.py`, `tests/test_report_export.py` |
| GAP-XCH-01 (partial) | Register exchange now exports activities/resources/risks as XLSX and imports resources from XLSX (`format=xlsx`, base64 payload), validated through the same rule set as CSV; CSV remains the default. No XML register import and no activity/WBS import yet. | `exchange_application.py`, `tests/test_exchange_api.py` |

Resolved after the review snapshot: **GAP-BAS-03** — `p6-baseline-capture-api.v1` now captures the latest published schedule snapshot as immutable baseline activities from the Cost Overview; merged implementation `b04d851`, browser-verified at `2a1c6b3` with evidence `1b367ba`. The older GAP-COST-01 browser note that seeded baseline rows manually is superseded by the capture journey.

Also resolved after the review snapshot: **GAP-PRJ-02** — `project-status-api.v1` stores the General-tab project status (Active/Inactive/Planned/What-If) under the `settings_revision` optimistic token and appends one immutable `project_lifecycle_status_event` per accepted change in the same transaction; a same-status save is a no-op, so retries cannot duplicate history. The Project settings dialog loads the stored status and renders the event history in en and fa; browser-verified in `apps/web/e2e/project-status-v26.mjs`, with live PostgreSQL coverage in `tests/integration/test_project_status_postgres_live.py`. What remains under the old gap name is narrower: there is no close/archive operation beyond the status field and no EPS/OBS hierarchy.

Also resolved after the review snapshot: **GAP-PRG-02** — `p6-activity-progress-history-api.v1` appends an immutable progress event inside the same transaction as each revision-guarded activity PATCH and reviews persisted actual dates against stored FS/SS/FF predecessors at write time (a persisted-fact comparison, not a rescheduled forecast). The Progress window renders the event log, the persisted percent-complete trend and a per-event out-of-sequence flag; browser-verified in `apps/web/e2e/progress-history-v26.mjs`, with live PostgreSQL repository coverage in `tests/integration/test_activity_progress_history_postgres_live.py`. Remaining sub-gaps: no all/selected bulk update, no stored EVM or cost/unit period actuals on this page, and the trend is the persisted percent series rather than a schedule-data dashboard.

Non-blocking gaps, recorded per surface in the two traceability matrices:

- Exchange imports only resources; CSV and XLSX are supported, but there is no XML register import
  and no activity/WBS/assignment/cost import (GAP-XCH-01, partially resolved on the branch below).
- Backup is project-scoped, non-destructive and without scheduling, retention, encryption or offsite
  copies (GAP-BKP-01).
- Reports have no scheduling, parameters, grouping, charts or export pipeline.
- Risks are not yet assigned to activities/resources and have no response action plan or
  risk-to-issue conversion; thresholds support three monitoring parameters with manual runs.
- Preferences do not yet drive formatting/precision/fiscal calendars elsewhere; there is no user
  directory or security-profile editor.
- Administration, risk, threshold, exchange and backup facts are SQLite-only; the Postgres mirror is
  not exercised for them by the default suite. Progress-history events do have a Postgres repository, covered by
  `tests/integration/test_activity_progress_history_postgres_live.py` in the PostgreSQL Integration workflow.
- Long-tail schedule dialogs are not line-by-line audited (GAP-SCH-01) and translated-string coverage
  for the six non-authored locales is unverified (GAP-I18N-01).
- New labels are inline English/Persian rather than part of the locale dictionaries.

## 6. Verdict

Every Version 26 workspace module in scope is implemented, wired to authoritative persisted data,
reachable from the canonical workspace shell, and covered by unit, repository/API, HTTP,
permission/revision and browser evidence on the final `main`. The remaining items are the external
parity blocker, five server-side capability gaps, and the recorded non-blocking product and audit
gaps above. No module is left as a silent placeholder: each either performs real persisted work or
states why it cannot.

## 2026-11-12 addendum — Activities chrome

The Activities menu bar, icon toolbar, chart board controls and both vertical rails were re-audited
and aligned to the Version 26 toolbar topics at code SHA
`9ddb1fa235eb20c89339e73622719ffb1915cb99`. Twelve requirements measure as MATCH and eight as
PARTIAL (named command absences, not structural defects); there is no GAP row in this increment.
Evidence: `docs/workspace/evidence/toolbars-v26-2026-11-12/report.json` and
`docs/qa/V26_TOOLBAR_COMPLIANCE_MATRIX_2026-11-12.md`.
