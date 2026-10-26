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
- POST /api/projects/{project_id}/ai/actions/proposals/{proposal_id}/execute: body carries expected_revision and an optional IANA timezone used only for post-execution authoritative recalculation.

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

The branch includes an earlier `main` merge commit `7eaeea4fda70f447c4ad1969d52a18ffaaac8ceb`, which contains the SQLite Activity Master transaction-ownership fix from PR #1548 (`7eaeea4fda70f447c4ad1969d52a18ffaaac8ceb` is the squash merge SHA). Its repository save method now preserves caller-owned transactions and only commits/rolls back transactions it started itself. This is an enabling persistence correction, not evidence that this AI runtime is already bound to the Activity Master handler or that proposal state, audit and business mutation share one production transaction.

The runtime code head was realigned to main `08df9d00fefaca8be61689a930752a9e0df3683e` on 2026-10-26 through a normal merge. The upstream "sync latest main" resolution had dropped branch-only implementation files; the reconciliation merge restored them while retaining main's Resource Dependent scope documentation and PR #1575 identity validation. See the governance ledger for exact heads and CI.

## Typed project mutation vertical slices — 2026-10-25/26

The branch now includes two explicit typed production tools, `activity.create` and `activity.update`, in `src/construction_pm/ai_action_activity_tools.py`:

- Each tool validates a bounded payload and constructs or patches the existing `ActivityMaster` domain record. It writes only through the authenticated `P6ActivityMasterAPI` and its configured Activity Master repository; it does not write directly around the application API.
- `activity.update` accepts only `activity_id`, `expected_revision`, `name`, `duration_value` and `duration_unit`. Activity identity and record revision are required, at least one mutable field must be present, duration value/unit must be supplied together, and a finite nonnegative Decimal duration plus a valid unit is enforced. Unknown fields, mass assignment, actual dates, progress, status, relationships and resource fields are rejected. The API fresh-reads the record, applies a field-limited patch to the validated domain model, and saves with the caller's expected record revision.
- Request identity, tenant, project, roles and revision are passed from the authenticated `ProjectLifecycleHttpRoutes` context. Client-supplied identity or approval-policy fields are not accepted as authority.
- An explicitly composed runtime requires the real Activity Master repository, authorization policy, current-grant adapter and transaction manager. It fails closed if a dependency is absent, a storage adapter is unsupported, or the runtime/proposal/audit/idempotency/repository connection identities do not match.
- The scoped idempotency record and Activity Master mutation are written in the same authoritative DB transaction, keyed by proposal ID and bound to a request fingerprint.
- The runtime reserves `approved → executing` before the business transaction and persists the final result in a subsequent transaction. A late handler/commit error rolls the business mutation and idempotency result back when the DB transaction aborts; the durable execution reservation becomes `uncertain`, blocking ordinary replay.
- Current grants are checked before reservation and again immediately before the real handler. If a grant is revoked between those checks, the handler is not called; the proposal is moved to a terminal `denied` state and denial is audited.
- A stale project revision is terminalized as `stale` after the denial audit is persisted outside the rolled-back transaction. Tests verify it cannot be approved again. A stale activity record revision, missing activity or duplicate create is a guaranteed no-mutation rejection and is terminalized as `blocked`, never `uncertain`; the Web panel labels it as a precondition failure and asks for a new proposal based on current data.
- If recording the resulting state/audit fails, the existing `executing` reservation remains non-replayable and the HTTP error avoids suggesting an unsafe retry.
- Tests cover authenticated HTTP proposal → approval → execute for create and update, client identity/approval-policy spoofing, grant revocation before and after reservation, stale project revision, stale record revision, missing activity, mass-assignment and duration-pair rejection, invalid payload, split-connection rejection, rollback/no replay after executor error, SQLite fresh-connection read-back, and a live PostgreSQL fresh-connection read-back.

The exact revision-locked update path was added after the first create slice; both tools share the runtime, authorization, approval, execution-reservation, audit and verification boundaries described below.

## Post-execution authoritative recalculation — 2026-10-26

After a successful, authorized `activity.create` or `activity.update` execution, the HTTP boundary performs a read-after-write verification through the existing authoritative components:

- It fresh-reads the persisted activity with `P6ActivityMasterAPI.get`; the executor's returned DTO is not treated as the source of calculated truth.
- It publishes an immutable schedule input snapshot and calculation context through `P6ScheduleSnapshotPublicationAPI.publish`, which requires the current `project.schedule` permission and composed project schedule settings.
- It executes a FACT `ScheduleQueryAPI` request against that snapshot. `AuthoritativeScheduleQueryProvider` materializes and evaluates the immutable snapshot through the Shared Calculation Core. No additional CPM engine is introduced.
- The execute response adds an `execution_verification` object under the strict `ai-action-execution-verification.v1` contract with status `COMPUTED`, `UNAVAILABLE`, or `FAILED`. `validate_execution_verification` rejects unknown fields, malformed activity/snapshot/query identities, non-finite or negative durations, invalid reason codes, a `COMPUTED` result without calculated fields, and a non-`COMPUTED` result carrying invented calculated fields. A computed result carries the fresh-read duration unit plus the calculated start, finish, duration (when projected), critical flag (when projected), project finish, calculation run identity, snapshot id/hash/calculation identity, and query id.
- The verification is also stored in the AI action store, one scoped record per tenant/project/revision/proposal, with an audit event and the previous status. Proposal list/detail reads are revision-filtered and validate the stored payload before returning it; malformed stored data fails explicitly rather than presenting a ghost result. If storing the verification fails, the committed action and the computed response are still returned; the response reports `execution_verification_stored: false` and no durable copy is claimed.
- Verification failures never roll back or hide the committed action. Missing composition, missing schedule permission, a missing calculation timezone, and unreadable settings produce an explicit `UNAVAILABLE`/`FAILED` reason instead of fabricated dates. The Web panel displays the computed start/finish or an explicit unavailable/failed message and does not render the raw action result JSON. A `COMPUTED` verification whose activity identity does not match the persisted result is rejected before storage.
- Replaying the same proposal is still rejected by the runtime before any second mutation or snapshot publication.

The regression tests cover permission denial before proposal creation, write-without-schedule permission (mutation retained, recalculation UNAVAILABLE), approval enforcement before mutation, real persistence read through a fresh SQLite connection, snapshot publication containing the persisted activity, Shared Core FACT recalculation, durable verification read through a fresh connection and proposal list/detail, duplicate-execution rejection, verification-store failure without masking the committed action, revision-isolated and malformed stored verification, missing settings (FAILED without ghost success), missing timezone (UNAVAILABLE), stale record revision, missing activity, mass assignment, and revision-locked update.

Verified on reconciliation head `3461e8423491602ae66598bd45091c06b15b46db`:

- [ConstructionPM CI #40276694112](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40276694112) — PASS on Python 3.11, 3.12 and 3.13.
- [PostgreSQL Integration #40276694100](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40276694100) — PASS.
- [Client Typecheck #40276694174](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40276694174) — PASS for Web, Desktop, Mobile and Client Sync.
- [ConstructionPM Web CI #40276694131](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40276694131) — PASS.
- Local Python: full suite `2801 passed, 124 skipped`; focused scheduling/AI suites `200 passed`. PostgreSQL integration remains skipped locally because `P6_TEST_POSTGRES_DSN` is not configured; the dedicated PostgreSQL workflow passed.
- Local Web under the available Node 26 type-stripping loader: `232 passed, 9 failed`; all 9 failures are unrelated runner limitations (TypeScript parameter properties, a type-only export, and a cwd-relative module path) outside the changed AI/scheduling surfaces. The official `npm test`/`tsc` local run remains blocked by unavailable npm dependencies, so the exact-head Client Typecheck and Web CI results above are the authoritative type/build evidence.
- Real browser E2E against a live WSGI route composition, SQLite and the Shared Core: create update proposal → approve → execute → `COMPUTED` start `2026-10-19`, finish `2026-10-22`, duration `4` working-day, critical `yes`, persisted activity record revision `2`; full page reload and list re-open returned the same stored verification. A second update with stale record revision `1` returned HTTP 409, was stored as `blocked` with no result and did not mutate the activity; removing the session cookie produced `SESSION_REQUIRED` with a Retry action and no fabricated data. The harness is an external test fixture, not committed production code.

Deliberate boundaries of this slice:

- Verification is durable only as one latest record per proposal. It is not an append-only calculation-history series; a future revision or recalculation does not create a new verification version.
- The FACT projection for date-based schedules exposes duration and critical flags. The time-based projection exposes start/finish only, so verification reports those fields as null rather than inventing them.
- `activity.create` and `activity.update` have execution-time verifiers. Other tools remain proposal/execution boundaries until their own authoritative read-after-write checks exist.
- `activity.update` cannot write actual dates, progress, retained logic, relationships, resources, cost or baseline data. Greater project-edit coverage remains open.
- This is not full AI Assistant V1 or broader scheduling compatibility certification.

## Current acceptance boundary

The runtime and authenticated HTTP seam are an incremental integration, not a complete assistant. The model/provider orchestration and Web chat implementation described above are explicitly opt-in and remain pending until PR #1553 is merged and verified on its exact main SHA. The application must supply the real current-grant provider, authorized action runtime, repository and transaction manager; model credentials are server-only. `activity.create` and `activity.update` now have execution-time Shared Core recalculation and store the latest verification per proposal for later reads, but append-only verification history, verification for other tools, broader project editing, file/voice intake, durable multi-session transcripts, authoritative report generation, admin knowledge research/review/publication, privacy-safe generalization, backup/restore, and complete V1 cross-client acceptance remain open. Missing configuration or unsupported operations must continue to fail closed.
