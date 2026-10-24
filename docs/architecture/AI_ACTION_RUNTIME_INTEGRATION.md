# CUBI AI Action Runtime — Web Integration Contract

**Status:** Initial authenticated execution seam; not certification of the full AI Assistant V1.

## What the code provides

- The new module src/construction_pm/ai_action_runtime.py defines trusted request scope, a server-owned tool registry, durable proposal records, exact-scope permission checks, human approval, action execution, and append-only audit events.
- The Web route layer exposes the proposal, decision, and execution endpoints only when an AIActionRuntime is explicitly supplied.
- Production composition passes through that optional runtime. An absent runtime returns 404 ROUTE_NOT_FOUND; no default-allow tools are created.
- SQLiteAIActionRuntimeStore and PostgresAIActionRuntimeStore implement the same SQL contract. They use the connection supplied by the deployment; transaction and connection-pool ownership remain with the application layer.

## Endpoints

All endpoints require the existing cp_session cookie and an authenticated user who has the current project's project.write permission. expected_revision is mandatory.

- GET /api/projects/{project_id}/ai/actions/proposals: lists up to 100 recent proposals in the authorized project scope.
- GET /api/projects/{project_id}/ai/actions/proposals/{proposal_id}: reads one proposal in the authorized project scope.
- POST /api/projects/{project_id}/ai/actions/proposals: body carries expected_revision, registered tool_name, validated payload, and optional evidence_refs.
- POST /api/projects/{project_id}/ai/actions/proposals/{proposal_id}/decision: body carries expected_revision and Boolean approved.
- POST /api/projects/{project_id}/ai/actions/proposals/{proposal_id}/execute: body carries expected_revision.

Every route requires the existing cp_session cookie. Proposal list/detail requires project.write because returned payloads can contain actionable changes; it is not exposed to a read-only viewer. Decision and execution additionally recheck the exact current AI tool grant and current project revision. User, tenant, roles, project revision, tool action/domain and approval policy are derived server-side. Client-supplied tenant_id, requested_by and requires_human_approval are not authorization inputs.

## Mandatory deployment wiring before real project actions can ship

1. Supply a trusted grant provider that loads current grants at each decision; grants must match subject, tenant, project, revision, data domain, operation and exact tool.
2. Register only typed handlers for real application use cases. Never register a handler that writes directly around ordinary repository/application authorization.
3. Each handler must enforce proposal.project_revision_id as an optimistic-lock precondition inside the authoritative write transaction and use proposal.proposal_id as its idempotency key.
4. Configure the deployment's transaction manager to commit/rollback proposal, state-transition and audit writes at the correct request boundary. Do not share this store connection with an unrelated active business transaction unless that transaction is deliberately owned by the caller.
5. Ensure handlers invoke the authoritative Shared Domain/Calculation Core for schedule/resource/cost/progress calculations; this runtime is orchestration and must not implement a parallel calculation engine.
6. Add integration tests with the real grant repository, each registered tool/use case, persistence read-back through a fresh connection, cross-tenant denial, grant revocation between approval and execution, stale-revision conflicts, idempotency replay, and failure/compensation behavior.

## Executor error and uncertain outcome

If a registered handler raises after the runtime has moved a proposal to `executing`, the runtime records `uncertain` and audits `execution_outcome_uncertain`. It does **not** claim the project mutation definitely failed, and normal execution cannot replay an uncertain proposal. This protects against duplicate writes when a handler may have committed before its response was lost.

This is deliberately fail-closed, not a complete recovery system. An operator/reconciliation workflow must compare the proposal/idempotency key with authoritative project state and then resolve the outcome; until that exists, uncertain proposals remain a release blocker. Tool handlers still need idempotency and optimistic-lock enforcement inside the authoritative transaction, plus fresh-connection verification.

## Mainline alignment — 2026-10-25

The branch now includes the current `main` merge commit `7eaeea4fda70f447c4ad1969d52a18ffaaac8ceb`, which contains the SQLite Activity Master transaction-ownership fix from PR #1548 (`7eaeea4fda70f447c4ad1969d52a18ffaaac8ceb` is the squash merge SHA). Its repository save method now preserves caller-owned transactions and only commits/rolls back transactions it started itself. This is an enabling persistence correction, not evidence that this AI runtime is already bound to the Activity Master handler or that proposal state, audit and business mutation share one production transaction.

The runtime code head was realigned to current main on 2026-10-25. New exact-head CI must pass on the resulting commit before this PR is eligible for merge. The release blockers listed below remain open.

## First real project mutation vertical slice — 2026-10-25

The branch now includes an explicit first typed production tool, `activity.create`, in `src/construction_pm/ai_action_activity_tools.py`:

- The tool validates a bounded payload and constructs the existing `ActivityMaster` domain record. It writes only through the authenticated `P6ActivityMasterAPI` and its configured Activity Master repository; it does not write directly around the application API.
- Request identity, tenant, project, roles and revision are passed from the authenticated `ProjectLifecycleHttpRoutes` context. Client-supplied identity or approval-policy fields are not accepted as authority.
- An explicitly composed runtime requires the real Activity Master repository, authorization policy, current-grant adapter and transaction manager. It fails closed if a dependency is absent, a storage adapter is unsupported, or the runtime/proposal/audit/idempotency/repository connection identities do not match.
- The scoped idempotency record and Activity Master mutation are written in the same authoritative DB transaction, keyed by proposal ID and bound to a request fingerprint.
- The runtime reserves `approved → executing` before the business transaction and persists the final result in a subsequent transaction. A late handler/commit error rolls the business mutation and idempotency result back when the DB transaction aborts; the durable execution reservation becomes `uncertain`, blocking ordinary replay.
- Current grants are checked before reservation and again immediately before the real handler. If a grant is revoked between those checks, the handler is not called; the proposal is moved to a terminal `denied` state and denial is audited.
- A stale project revision is terminalized as `stale` after the denial audit is persisted outside the rolled-back transaction. Tests verify it cannot be approved again.
- If recording the resulting state/audit fails, the existing `executing` reservation remains non-replayable and the HTTP error avoids suggesting an unsafe retry.
- Tests cover authenticated HTTP proposal → approval → execute, client identity/approval-policy spoofing, grant revocation before and after reservation, stale revision, invalid payload, split-connection rejection, rollback/no replay after executor error, SQLite fresh-connection read-back, and a live PostgreSQL fresh-connection read-back.

Last verified code/test head before this documentation-only update: `bf110ac62b9ff88539ced03b6bd16952df83a4de`.

- ConstructionPM CI: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930835 — PASS on Python 3.11, 3.12 and 3.13.
- PostgreSQL Integration: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930827 — PASS.
- Client Typecheck: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930828 — PASS for Web, Desktop, Mobile and Client Sync.

This is **one real Activity Master create slice**, not the whole assistant. No AI model/provider orchestration or natural-language tool selection is wired; no WBS, relationship, calendar, resource or cost mutation tool is registered; the tool does not itself run a new Shared Core schedule calculation or ground a report in its resulting run identity; voice/document/Excel intake and preview, final assistant UI/report/chart/export, and operator reconciliation/recovery remain open.

## Current acceptance boundary

The runtime and authenticated HTTP seam are implemented as an incremental integration, not a complete assistant. Until deployment wiring and the above integration tests pass on an exact merged main SHA, the following remain open: real project-creation/editing tools, model/provider orchestration, document/voice intake, authoritative result grounding/report generation, admin knowledge research/review/publication, generalization privacy review, and client UI wiring. The runtime does not silently infer or enable any of these.
