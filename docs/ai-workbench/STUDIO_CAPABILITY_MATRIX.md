# Studio Capability Matrix

Status at this change: Phase 1 integrated; Risk and Project Analysis advanced in
parallel.

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
| Project Analysis Studio | `WIRED_READ` | workspace read v2 + control metrics | none | `http/project_lifecycle_routes.py` | record counts, stored metric bars, source refs |
| Decision & Approval Workspace | `PARTIAL` | Enterprise approvals exist | no Engineering proposal contract | `enterprise` approvals | partial panel; no proposal control |

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
  the returned rows. These are record counts, explicitly **not** a performance
  index.
- Displays control-intelligence metrics exactly as stored, with result id,
  generation time and source references.
- Cost/EVM and resource/forecast sections are declared `PLANNED`; no baseline
  or currency is selected and no value is calculated in the browser.
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

## Decision & Approval (PARTIAL)

- Enterprise approvals are wired, but there is no Engineering proposal store
  bound to a scenario revision and no execution contract with reauthorization,
  atomic apply, audit and read-back.
- No "approve" or "apply" button is offered until that contract exists.

## Parallel-engine prohibitions

No studio may add: a CPM/leveling/cost/EVM engine, a second import engine, a
second scenario model, a second risk store, or a second workflow/approval
model. A missing capability stays `BLOCKED`/`PLANNED` until its canonical
service lands.
