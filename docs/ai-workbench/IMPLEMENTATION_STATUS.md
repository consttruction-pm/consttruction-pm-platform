# Implementation Status

Updated: Phase 1 integration, 2026-11-21.

- Repository: `consttruction-pm/consttruction-pm-platform`
- Base: `eed937de1` (PR #2093, command foundation)
- Branch: `feat/ai-workbench-phase1`
- Status vocabulary: `LIVE_VERIFIED`, `WIRED_WRITE`, `WIRED_READ`, `PARTIAL`,
  `SHELL_ONLY`, `PLANNED`, `BLOCKED`, `HELP_REFERENCE_PENDING`.

## Phase status

| Phase | Scope | Status | Evidence |
|---|---|---|---|
| 0 | Audit, ownership, command layer | DONE | PR #2093 merged as `eed937de1` |
| 1 | Workbench shell, document route, command panel, HTTP endpoint, context resolver, inspector, status bar, states, authorization, audit log | IMPLEMENTED — see verification below | this branch |
| 2 | Risk Analysis Studio | WIRED_WRITE | create + edit (`expected_revision`) + audit history against `risk_api.py` |
| 3 | Project Analysis Studio | WIRED_READ | workspace read v2 + baseline register + canonical earned-value read; `INSUFFICIENT_DATA` when no baseline |
| 4 | Import staging (7 tabs) | PARTIAL | register exchange only; no project import engine |
| 5 | Schedule Scenario Studio | BLOCKED | no revision-bound scenario service (#1989) |
| 6 | Decision & Approval | PARTIAL | no Engineering proposal/execution contract |
| 7 | Integrated acceptance | PENDING | cross-phase gates not yet run |
| 8 | Enterprise reuse | PLANNED | after shared contracts stabilise |

## Phase 1 delivered

Server:

- `src/construction_pm/ai_workbench/http.py` — `AIWorkbenchHttpMiddleware` with
  `GET .../workbench/context` and `POST .../workbench/command`, session and
  project authorization, stable errors, body limits, structured audit log.
- Wired into `preview/runtime.py` and `deployment/production_runtime.py` with a
  real data-date provider in both runtimes.

Client:

- `apps/web/ai-workbench.html`, `apps/web/ai-workbench.css`,
  `apps/web/src/ai-workbench-entry.ts` (own bundle).
- `apps/web/src/workbench/{api,model,render,mount}.ts` — project chooser,
  command panel, four-block plan, studio tabs, risk studio, analysis studio,
  blocked/partial studios, inspector, status bar, Help inventory, locale switch,
  offline indicator.
- Enterprise → AI Workbench command in the desktop menu, localized for all ten
  locales, opening the active project and language.

Routing:

- Preview and production `/ai-workbench` document gates; `_safe_next` keeps only
  `project`, `lang`, `studio`; static document and stylesheet mapping. The
  Engineering shell is never served for this path.

## Verification run in this change

| Check | Result |
|---|---|
| `pytest tests/test_ai_workbench_http.py tests/test_ai_workbench_orchestration.py` | 47 passed |
| `pytest tests/test_production_web_app.py` | 34 passed |
| `pytest tests/test_preview_runtime.py` | 26 passed |
| `npm test` (web) | 1276 + 16 passed, 0 failed |
| `npm run typecheck` | clean |
| `npm run build` | bundles emitted |
| `node e2e/preview-e2e.mjs` | 112 recorded checks (see the run log attached to the PR) |

The browser journey drives the real preview runtime: document gate, planner
sign-in, empty risk state, risk create and read-back across a full reload,
deterministic command plan, blocked scenario studio with zero controls, stored
analysis counts, and Persian RTL / English LTR switching.

## Honest gaps

1. Import staging has no project-import engine; only register exchange exists.
2. Schedule scenarios have no persisted contract.
3. Decision/approval has no Engineering proposal or execution contract.
4. Every studio Help status is `HELP_REFERENCE_PENDING`; no fabricated URL. The
   document row `ENG-WS-AI-WORKBENCH` is registered as `CUBI_OWNED` with no
   official topic.
5. Workbench-specific UI strings use the shared localization system but most
   non-English catalogs do not yet contain them; the document shows an explicit
   fallback notice for non-English locales.
6. Risk delete, scenario promotion and approval execution are not exposed;
   risk create and update are wired.
7. The EVM studio requires an explicit baseline, currency and data date. The
   preview seed has no cost-loaded baseline, so the canonical read returns
   `EARNED_VALUE_REMAINING_COST_REQUIRED`; the studio shows that code rather
   than inventing figures. Resource/forecast remains `PLANNED`.
8. Production PostgreSQL is wired and compiles, but the browser journey runs
   against the preview SQLite runtime.

## Next executable tasks

1. Phase 4: implement the seven-tab import review against the project exchange
   contract once #1799 exposes project-level ingestion; keep register exchange
   as the only write today.
2. Phase 5: design the revision-bound scenario store with #1989; do not add a
   parallel scheduler.
3. Phase 6: proposal contract bound to scenario revision with reauthorization,
   atomic apply, audit and read-back.
4. Help: publish a CUBI-owned Workbench Help page. The document entry
   `ENG-WS-AI-WORKBENCH` is already registered (`CUBI_OWNED`, no topic), so a
   verified page can flip the per-studio status from `HELP_REFERENCE_PENDING`.