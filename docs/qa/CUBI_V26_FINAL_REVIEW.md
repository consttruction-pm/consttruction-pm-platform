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
| GAP-BAS-03 | Core/server | No HTTP route captures the current schedule into a baseline | Cost/EVM cannot run on an empty-baseline project; the page states this honestly |
| GAP-PRJ-02 | Core/server | No close/archive/status lifecycle operation | The Project page cannot offer those actions without fabricating them |
| GAP-DOC-02 | Core/server | No binary upload/download route | Documents store metadata plus `storage_ref` and SHA-256 only |
| GAP-PRG-02 | Core/server | No persisted progress-update log or out-of-sequence review | Progress edits are revision-guarded but not historically logged |
| GAP-TRK-01 | Core | No tracking read model | The Tracking window remains an honest shell |

Non-blocking gaps, recorded per surface in the two traceability matrices:

- Exchange imports only resources and only CSV; no XLSX/XML, no remote-project exchange
  (GAP-XCH-01).
- Backup is project-scoped, non-destructive and without scheduling, retention, encryption or offsite
  copies (GAP-BKP-01).
- Reports have no scheduling, parameters, grouping, charts or export pipeline.
- Risks are not yet assigned to activities/resources and have no response action plan or
  risk-to-issue conversion; thresholds support three monitoring parameters with manual runs.
- Preferences do not yet drive formatting/precision/fiscal calendars elsewhere; there is no user
  directory or security-profile editor.
- Administration, risk, threshold, exchange and backup facts are SQLite-only; the Postgres mirror is
  not exercised for them by the default suite.
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
