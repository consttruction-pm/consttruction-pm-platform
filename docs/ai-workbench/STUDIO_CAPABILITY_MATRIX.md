# Studio Capability Matrix

Status at this change: Phase 7 security gates and Phase 6 Decision & Approval
wired where the canonical runtime is mounted.

Legend: `LIVE_VERIFIED` — read/write exercised end to end against the real
runtime. `WIRED_WRITE` — canonical read and write service connected and tested;
full cross-phase acceptance may still be pending. `WIRED_READ` — canonical read
service connected and tested. `PARTIAL` — some canonical services exist, the
full studio contract does not. `BLOCKED` — the canonical service is absent.

| Studio | Status | Read | Write | Canonical service | Client surface |
|---|---|---|---|---|---|
| Project Import Review & Staging | `PARTIAL` | register datasets (`exchange`) | register import only | `exchange_api.py` | honest partial panel; no project-import controls |
| Schedule Scenario Studio | `BLOCKED` | schedule read exists but no scenario contract | none | none | blocked panel: service, reason, Help topic; zero controls |
| Risk Analysis Studio | `WIRED_WRITE` | `GET /api/projects/{id}/risks` (+ `/history`) | `POST` create, `PUT` update with `expected_revision` | `risk_api.py` / `risk_application.py` | table, 5×5 matrix, inspector, create and edit forms, audit history |
| Project Analysis Studio | `WIRED_READ` | workspace read v2 + control metrics + `GET .../p6/baselines` + `POST .../p6/earned-value` | none | `project_lifecycle_routes.py`, `p6_earned_value_read_model_api.py` | record counts, stored metric bars, source refs, baseline-driven EVM |
| Decision & Approval Workspace | `WIRED_WRITE` when the canonical runtime is mounted, otherwise `PARTIAL` | `GET .../ai/actions/proposals` | `POST .../decision`, `POST .../execute` with `expected_revision` | `ai_action_runtime.py` / `ai_action_boundary.py` | proposal list, approve/reject, execute-if-approved, stale guard, canonical result |

## Risk Analysis Studio (WIRED_WRITE)

- Reads the full register for the pinned tenant/project through the risk API.
- Groups stored `probability × impact` into a fixed 5×5 matrix. No rating, score
  or exposure is recalculated in the browser; `score` and `exposure_level` come
  from the server.
- Create form collects risk ID, title, description, category, probability,
  impact, owner, response strategy and date identified. The client validates
  presence and 1–5 bounds only; the server validates the domain contract.
- Each draft risk carries one idempotency key; a conflict triggers a fresh read
  rather than a duplicate write.
- The inspector edits an existing risk through `PUT` with the rendered
  `expected_revision`; a `409` re-reads the register instead of overwriting a
  newer record. A success notice reports the revision the server returned.
- The inspector's history view reads `GET …/risks/{id}/history` and renders the
  stored audit events (create, update or status change) with actor, time and
  reason. It never synthesises an event.
- Empty state: "No risk is stored for this project revision. Nothing is
  generated for display."

Accepted categories: `technical`, `commercial`, `schedule`, `cost`, `quality`,
`safety`, `resource`, `external`. Strategies: `avoid`, `transfer`, `mitigate`,
`accept`, `escalate`. Status: `open`, `monitoring`, `mitigating`, `closed`.

## Project Analysis Studio (WIRED_READ)

- Reads `GET /api/v2/workspace/control-room/read` with the pinned tenant,
  project and revision headers.
- Counts activities, WBS elements, relationships and critical activities from
  the returned rows: `workspace.activities`, the canonical
  `workspace.wbs_nodes` collection (with the older `workspace.wbs` name still
  read for compatibility) and `workspace.relationships`. These are record
  counts, explicitly **not** a performance index.
- Displays control-intelligence metrics exactly as stored, with result id,
  generation time and source references.
- Lists the stored baselines through `GET .../p6/baselines`. When none exists it
  shows `INSUFFICIENT_DATA` and renders no EVM control.
- When a baseline exists, the operator selects it and states the currency and
  data date; the studio calls `POST .../p6/earned-value` and renders the
  returned snapshot (PV, EV, AC, CV, SV, CPI, SPI, EAC, VAC, ETC method)
  verbatim. A refusal is shown as the server code; no value is ever estimated
  in the browser.
- Resource/forecast remains `PLANNED`; no baseline or currency is guessed.
- `409 STALE_WORKSPACE_READ_SCOPE` is shown as the server code with a retry.

## Import Staging (PARTIAL)

- The repository has no project-level import engine (EPS/projects/WBS/
  relationships/calendars/baselines). Register exchange imports four datasets
  only.
- The studio therefore renders its status, service and reason and offers no
  import, mapping or preview control. The seven-tab contract remains a design
  gate (`PROJECT_IMPORT_STAGING_SPEC.md`).

## Schedule Scenario (BLOCKED)

- The Shared Scheduling Core exists, but there is no revision-bound scenario
  entity, run history, comparison or promotion service (Issue #1989).
- The studio renders `BLOCKED` with the canonical service name and reason and
  renders no control. Returning a blocked command never opens another studio.

## Decision & Approval (WIRED_WRITE where the runtime is mounted)

- Reads proposals from the canonical `AIActionRuntime`, scoped by the session
  tenant, project and project revision. The proposal list requires project write
  access; a read-only session sees an explicit read-only state and no list.
- A proposal does not change project data. Approve/reject records a decision;
  execution reauthorizes the exact tool grant, checks the pinned revision and
  applies the change through the registered tool (activity/project-plan).
- Every action sends `expected_revision`; `409 AI_ACTION_PROPOSAL_STALE_REVISION`
  re-reads the context and list instead of resubmitting.
- A proposal whose `project_revision_id` no longer matches the context is marked
  stale by the server; the studio shows only a warning and offers no control.
- Before a decision, an `activity.create` proposal is shown as a literal
  before/after table against the canonical workspace read of the same revision:
  the activity ID, name, WBS node and duration currently stored versus the
  proposed payload. An existing activity ID, an unknown WBS node and an
  unavailable current read are named as review warnings.
- That comparison is a record lookup, not a schedule simulation. It does not
  run CPM, leveling, cost or earned value and never estimates a date; the
  studio states this next to the table. Proposals for tools without a typed
  comparison show their canonical payload only.
- The preview composition mounts the runtime (`Capabilities(proposal_execution=
  True)`). A composition without it reports `PARTIAL`, names the missing service
  and renders no approval control.
- Scenario-specific approvals remain pending with the scenario service (#1989);
  the studio does not invent a scenario proposal model.

## Parallel-engine prohibitions

No studio may add: a CPM/leveling/cost/EVM engine, a second import engine, a
second scenario model, a second risk store, or a second workflow/approval
model. A missing capability stays `BLOCKED`/`PLANNED` until its canonical
service lands.
