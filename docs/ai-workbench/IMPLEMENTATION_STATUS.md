# Implementation Status

Updated: environment document routing and canonical workspace read, 2026-11-21.

## Environment document routing

The two products are separate documents on one origin: Engineering at `/app`,
Enterprise at `/cubi/*`, and the shared AI Workbench at `/ai-workbench`.
Reading the deployment entrypoints exposed three real routing gaps:

- The root `api/shell.py` forced `PATH_INFO` to `/app`, so any document routed
  through it became the Engineering shell. Both entrypoints now use the shared
  `deployment/workspace_routes.py` resolver, which accepts only `app`,
  `enterprise`, `cubi/*` and `ai-workbench/*` and falls back to `/app` for an
  unknown or traversing path.
- Neither `vercel.json` routed `/cubi` or `/ai-workbench`, so the deployed
  origin could not reach either document. Both now rewrite them to the
  session-gated shell, and the `__path` marker is removed from the user query
  before the boundary builds a post-login target.
- The deployment builds did not stage `enterprise.html`, `ai-workbench.html` or
  `ai-workbench.css`. The root build, the `apps/web` runtime stage and the Pages
  assembly now copy all three, and the `apps/web` project rewrites its two
  entry bundles to the flat build output.

The retired `/enterprise` address still returns `308` from the HTTP boundary to
`/cubi/`; it never serves the Engineering shell. `tests/test_workspace_shell_routing.py`
pins the resolver and the deployment configuration, and the browser journey now
checks both documents and their independent session gates.

## Workbench read and review corrections

- Project Analysis read the legacy `workspace.wbs` name while the canonical v2
  workspace contract returns `workspace.wbs_nodes`. The WBS count therefore
  displayed zero even when the read contained stored nodes. `analysisCounts`
  now reads `wbs_nodes` (the older name remains a fallback), and the browser E2E
  asserts a stored WBS count instead of only the activity count.
- The Decision & Approval studio now reads the canonical workspace of the same
  revision and shows an `activity.create` proposal as a literal current/proposed
  table before a decision. Existing IDs, an unknown WBS node and an unavailable
  read are explicit review warnings. This is a record comparison only: no
  schedule, cost or earned-value calculation runs and no date is estimated.
- The workspace cache is invalidated when the project revision advances, so a
  decision or execution cannot present a previous revision's comparison.

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
| 4 | Import staging (7 tabs) | PARTIAL | source stage `cubi-reference-import-source.v1` validates the 94-sheet workbook (0 errors); persistence/apply still needs the project import engine (#1799) |
| 5 | Schedule Scenario Studio | BLOCKED | no revision-bound scenario service (#1989) |
| 6 | Decision & Approval | WIRED_WRITE in the preview composition; PARTIAL elsewhere | canonical proposal list + approve/reject + execute with `expected_revision`; scenario-specific approvals still wait on #1989 |
| 7 | Integrated acceptance | PARTIAL | workbench boundary security gates proven; cross-phase (import, scenario, approval) acceptance waits on their contracts |
| 8 | Enterprise reuse | PLANNED | after shared contracts stabilise |

## Operationalization on the canonical database (P0)

The workbench now runs on the same production composition as the rest of the
site, not on a preview-only store. What changed and what is actually proven:

| Capability | Status | Where |
| --- | --- | --- |
| Versioned migration ledger (`cubi_schema_migration`, 15 steps, 94 tables) | `WIRED_WRITE` / verified on real PostgreSQL | `deployment/migrations.py`, `tests/integration/test_cubi_database_operationalization_postgres_live.py` |
| Project/workspace save and restore across logout and a new session | `WIRED_WRITE` | live PostgreSQL WSGI test, test 4 |
| Risk register (create idempotent, update with `expected_revision`, history) | `WIRED_WRITE` | `risk_persistence.py`, test 6 |
| Forms library (templates, immutable published versions, submissions, review/approval, audit) | `WIRED_WRITE` | `form_builder_repository.py` shared PG/SQLite base, tests 7–8 |
| Knowledge store on the caller-owned schema and coverage reporting | `WIRED_READ` | `knowledge/runtime.py`, `PostgresKnowledgeStore(..., migrate=False)`, test 12 |
| AI action proposals: propose → human approve → execute, stale-revision and duplicate guards | `WIRED_WRITE` | `ai_action_runtime.py`, tests 9–10 |
| Tenant isolation and role denial (viewer writes, cross-tenant reads) | verified | tests 3, 11 |
| Assistant with a real model provider | `BLOCKED` externally | needs `CUBI_AI_ENABLED` + provider key; deterministic planner otherwise |
| Supabase reference database / Vercel Preview | `BLOCKED` externally | no Supabase or Vercel credentials in the sandbox; runbook in `docs/deploy/PREVIEW_SUPABASE_CONNECTION.md` |

Every write above is gated by the session's tenant and roles and recorded in
the append-only audit/event tables. A proposal never mutates before approval;
execution re-checks the pinned revision and is idempotent, and a second execute
returns `409 AI_ACTION_PROPOSAL_NOT_APPROVED` instead of mutating twice.

The status vocabulary distinguishes local proof from deployment proof:
`WIRED_*` means the code path is exercised, and only a real Supabase + Preview
run may be labelled `VERIFIED_ON_SUPABASE`. No studio or assistant response is
fabricated to close a gap; unavailable capabilities return `BLOCKED`/`PARTIAL`
with the missing dependency named.


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
| `npm test` (web) | 1299 + 16 passed, 0 failed |
| `npm run typecheck` | clean |
| `npm run build` | bundles emitted |
| `node e2e/preview-e2e.mjs` | 127 recorded checks (see the run log attached to the PR) |

The browser journey drives the real preview runtime: document gate, planner
sign-in, empty risk state, risk create and read-back across a full reload,
deterministic command plan, blocked scenario studio with zero controls, stored
analysis counts, Persian RTL / English LTR switching, and the Enterprise
environment journey described in `TEST_AND_ACCEPTANCE.md` §5.

## Phase 6 Decision & Approval

Implemented in this change wherever the canonical runtime is mounted:

- the studio reads `GET /api/projects/{id}/ai/actions/proposals` through the
  shared transport; a read-only session sees an explicit read-only state and no
  list;
- approve/reject calls `POST .../proposals/{pid}/decision` and execution calls
  `POST .../proposals/{pid}/execute`, both with the pinned `expected_revision`;
- a stale revision re-reads the context and list instead of resubmitting; a
  proposal the server marks `is_stale` shows a warning and no control;
- the preview runtime passes `Capabilities(proposal_execution=True)` because it
  mounts the canonical `AIActionRuntime`; a composition without the runtime
  reports `PARTIAL` with the missing-service reason;
- the browser acceptance creates one `activity.create` proposal, rejects it in
  the studio, reloads and confirms the rejection persisted without creating the
  activity. Execution is covered by the existing canonical assistant journey on
  a separate project.

Scenario-specific approvals are still pending with the scenario service
(#1989); the studio does not invent a scenario proposal model.

## Phase 8 Assistant conversation in the Workbench

The command panel now speaks to the canonical assistant instead of only routing
keywords:

- `POST /api/projects/{id}/ai/assistant/turn` is called through the shared
  `AIActionClient`, the same client the workspace chat uses; there is no second
  prompt format, no local provider call and no client-side proposal creation;
- the transcript is bounded by the shared `boundedAIAssistantHistory` helper and
  renders only the server's messages; it never offers approve or execute;
- an `action_proposal` turn is stored by the server, the panel shows its id and
  opens Decision & Approval, where the existing revision-guarded approve/execute
  controls remain the only way to act;
- when the deployment has no provider (`AI_ASSISTANT_NOT_CONFIGURED`, or a
  provider 429/5xx/configuration error), the panel says so and routes the same
  sentence through the read-only deterministic planner. The browser run proves
  the fallback from the recorded response body, and any other 5xx still fails;
- a stale assistant revision re-reads the pinned context instead of resubmitting.

## Phase 7 security acceptance

Implemented in this change:

- the workbench router validates the project id after percent-decoding and
  rejects separators, `.`/`..` segments, control characters and over-long ids
  with `400 PROJECT_ID_INVALID` before any lifecycle lookup;
- `tests/test_ai_workbench_http.py` now runs 27 tests, including real
  `ProjectLifecycleService` cross-tenant cases (foreign project hidden, shared
  id resolved per tenant, provider receives the session tenant) and a
  body-override test proving the envelope is built only from the session and
  URL scope;
- `SECURITY_AND_AUTHORIZATION.md` and `TEST_AND_ACCEPTANCE.md` record the gates
  and the tests that prove them.

Still open in Phase 7: end-to-end acceptance for import staging, schedule
scenarios and decision/approval. Those studios have no write contract yet, so
there is no cross-phase flow to accept without inventing a parallel engine.

## Honest gaps

1. Import staging has no project-import engine; only register exchange exists.
2. Schedule scenarios have no persisted contract.
3. Decision/approval has no Engineering proposal or execution contract.
4. Each studio now records one verified studio-level Help reference
   (`HELP_REFERENCE_VERIFIED`) and the Inspector links it. Per-control deep
   links remain pending; the document row `ENG-WS-AI-WORKBENCH` is registered as
   `CUBI_OWNED` with no official topic.
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

## Assistant V1 minimum standard and gap-closure directive — 2026-11-22

The binding product standard, required internal tool families, service reuse/build/connect matrix, ordered execution phases and V1 Definition of Done are recorded in:

- `docs/architecture/AI_ASSISTANT_V1_MINIMUM_STANDARD_AND_GAP_EXECUTION.md`
- Execution issue: [#2125 — Complete CUBI AI Assistant V1 internal tools, service connections and execution gaps](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2125)

Issue #2125 supplements (does not replace) #2093, #2090, #2019, #1423, #1530, #1799 and #1989. The mandatory direction is one CUBI-owned assistant entry, the existing Command Orchestration Layer, one typed Assistant Tool Registry, canonical internal domain services, the single Shared Scheduling/Calculation Core, scoped authorization, explicit approval, revision checks, idempotent/transactional execution, fresh read-back and durable audit. No mandatory third-party AI provider, parallel domain engine, duplicate importer, browser-side authoritative calculation or fabricated capability is permitted.

The architecture document is a target standard and gap-closure plan, not a claim of completion. All capability statuses remain evidence-based; P0 release acceptance requires exact-head CI, real-browser and database proof.