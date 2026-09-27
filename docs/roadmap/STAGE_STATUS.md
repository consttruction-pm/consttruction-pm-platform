### Document Approval Lifecycle Boundary
Status: **100% — implemented; runtime-verified 2026-09-27 through PR #177**
- Added explicit draft/submitted/approved/rejected/superseded lifecycle transitions.
- Every transition requires expected revision and records actor, timestamp and optional reason in append-only audit history.
- Invalid transitions are rejected without mutation and status transitions preserve the persisted document payload.
- Role authorization, OCR/search and storage-provider behavior remain separate boundaries.

### P0 Document Persistence Boundary
Status: **100% — implemented; runtime-verified 2026-09-27 through PR #174**
- Added versioned `p0-document-resource` contract for contract, drawing, correspondence, RFI, submittal, delay-claim and evidence resources.
- Added PostgreSQL document metadata persistence behind an opaque storage reference.
- Enforced tenant/project scope, SHA-256 content-integrity metadata, idempotency replay/reuse protection, optimistic revision checks and append-only audit history.
- Added safe JavaScript revision-ceiling protection and focused contract/persistence regression tests.
- OCR/search engines, storage-provider implementations and approval policy remain separate boundaries.
- ConstructionPM CI and Client Typecheck passed on exact merged head for PR #174.

# Project Stage Status

| Stage | Status |
|---|---:|
| Scheduling/Calendar Engine | Completed through approved design and test specifications |
| Stage 32.3 Progress Rules & Calculation | 100% |
| Stage 32.4 Progress History/Audit/Revision | 100% |
| Stage 32.5 Progress Update Workflow | 100% |
| Stage 32.6 Dashboard & Control Center | 100% |
| Stage 32.7 Reporting & Print Engine | 100% |
| Stage 32.8 Resource & Cost Control Center | 100% |
| Stage 33 — System Integration & Platform Hardening | 36% — in progress |

Progress percentages refer to the documented development workflow, not a claim that production source code for every module already exists.

### Stage 33.4 — Production Web/Desktop/Mobile Client Foundation and Shared Client Integration
Status: **100% — completed; runtime-verified 2026-09-24**
- Scope document: docs/architecture/STAGE_33_4_WEB_DESKTOP_CLIENT_FOUNDATION.md.
- Web, Desktop and Mobile consume the same versioned API/Application contracts.
- Shared Domain/Calculation Core remains the single source of Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar and financial calculation semantics.
- No client-specific scheduling formulas are permitted.
- 33.4.8 Portable Shared Scheduling Core foundation: implemented.
- 33.4.9 Portable Activity + Forward Pass: implemented.
- 33.4.10 Backward Pass + Float Analysis: implemented.
- 33.4.11 Foundational Activity Date Constraints: implemented.
- 33.4 Offline Project Context backend contract: implemented.
- 33.4.12 Backward-Pass Constraint Integration: implemented.
- 33.4.13 ALAP / Schedule Options foundation: implemented.
- 33.4.14 Relationship Lag Semantics Hardening: implemented.
- 33.4.15 Combined Constraint + Relationship Hardening: implemented.
- 33.4.16 Backward Relationship Feasibility Hardening: implemented.
- 33.4.17 Advanced Constraint Set Validation: implemented.
- 33.4.18 Constraint Propagation Through Lagged Networks: implemented.
- 33.4.19 Constraint Propagation Across FS/SS/FF/SF + Lag/Lead: implemented.
- 33.4.20 Backward Constraint Propagation Across FS/SS/FF/SF + Lag/Lead: implemented; lower-bound propagation behavior superseded by the Stage 33.4.25 P6 semantic correction.
  - Relationship feasibility remains enforced in the backward schedule.
  - Start/Finish No Earlier Than are now treated as early-date constraints and do not move late dates.
  - Upper-bound and mandatory constraints remain subject to late-date validation.
- 33.4.21 P6 Constraint Semantics Matrix: implemented as Shared Core documentation baseline.
- 33.4.22 P6 Constraint Edge-Case Test Pack: implemented; obsolete lower-bound backward-propagation assertions were removed after the Stage 33.4.25 P6 semantic correction.
  - Relationship feasibility remains covered.
  - Full CI execution remains unverified.
- 33.4.23 Constraint + Float + Critical Path Reconciliation: implemented.
- 33.4.24 P6 Schedule Option + Constraint Interaction Pack: implemented.
  - EARLIEST and ALAP are tested with constrained FS/SS/FF/SF networks and positive lag.
  - Selected schedule remains mode-specific while Early/Late schedules and Float analysis remain preserved.
  - Added regression coverage preventing ALAP selection from mutating the Early schedule.
- 33.4 Offline Mutation Queue Retry Attempt: implemented and hardened through PR #50 (2026-09-24); retry attempts are persistent and transaction-aware, mutation identity/fingerprint remains stable, and SQLite enqueue is idempotent for the same mutation while rejecting conflicting reuse of an idempotency key.
  - Constrained late dates are reconciled against early dates before Total Float is accepted.
  - Negative constrained Total Float is rejected rather than hidden by clamping to zero.
  - Added constrained critical-path, ALAP, and holiday/calendar reconciliation tests.
  - Early/Late/Selected schedule separation remains intact.
  - Documents Forward/Backward behavior for all six implemented constraint types.
  - Documents calendar normalization, combined-constraint validation, relationship interaction, and backward-pass validity gates.
  - Formal P6 parity verification remains pending; the matrix is a compatibility specification, not certification.
- 33.4.25 Constraint Engine Final Hardening & Scheduling Core Review: implemented.
  - Reconciled P6 constraint scope: Start/Finish No Earlier Than affect early dates; Start/Finish No Later Than affect late dates; Mandatory Start/Finish affect both.
  - Removed backward propagation of lower-bound constraints into late dates.
  - Preserved negative Total Float as a valid P6 scheduling result and mark negative-float activities critical under the default zero threshold.
  - Added regression tests for lower-bound/late-date separation and negative float.
  - Full test execution remains unverified until CI/GitHub Actions executes the committed suite.
- Full P6 constraint semantics, exact P6 schedule-option parity, richer time-of-day calendars, and formal P6 parity certification remain pending.
- Full test execution is not marked as verified until CI/GitHub Actions executes the committed test suite.
- Tracking issue: #26.

### Stage 33.4-B — SQLite Transaction Boundary Hardening
Status: **100%**
- Application transaction rollback against SQLite persistence is regression-tested.
- Nested repository transactions participate in the outer application transaction.
- Stable stale-revision error mapping import reconciled.
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics changed.

- 33.4.26 Scheduling Core Parity & Edge-Case Certification Pack: implemented as a regression specification.
  - Added parameterized FS/SS/FF/SF coverage across negative/zero/positive lag.
  - Added deterministic input-order regression coverage.
  - Added holiday/weekend boundary, zero-duration, custom-calendar, constraint-scope, and EARLIEST/ALAP separation tests.
  - Added docs/architecture/SCHEDULING_P6_PARITY_CERTIFICATION_PACK.md.
  - This is a compatibility/regression pack, not formal Oracle certification.
  - Runtime CI execution remains unverified.

- 33.4.27 Time/Calendar Semantics Hardening: implemented as the Shared Core extension boundary.
  - Added WorkingTimeCalendar with working weekdays, holidays and multiple non-overlapping daily intervals.
  - Added TimeAwareWorkingTimeResolver for deterministic datetime normalization, working-hour addition and working-hour calculation.
  - Added regression tests for breaks, holidays, multi-interval shifts, Decimal hours and invalid durations.
  - Exported the time-aware resolver from the scheduling package.
  - Existing date-based Scheduling APIs remain unchanged until time-based duration/lag contracts are explicitly integrated and tested.
  - Full P6 time-of-day parity remains pending; runtime CI execution remains unverified.

- 33.4.28 Time-Based Duration & Lag Contract: implemented as an explicit Shared Core quantity foundation.
  - Added DurationUnit with WORKING_DAY and WORKING_HOUR.
  - Added Decimal-safe TimeQuantity for activity durations and signed LagQuantity for lag/lead.
  - Calendar conversion remains authoritative in the Shared Core resolver; no fixed 8-hours-per-day assumption was introduced.
  - Existing date-based Activity/Relationship/CPM APIs remain compatible and are not silently changed.
  - Full time-aware Forward/Backward/Float integration remains the next gate; runtime CI remains unverified.

- 33.4.29 Activity & Relationship-Lag Calendar Resolution: implemented as the authoritative calendar-selection foundation.
  - Added versioned CalendarReference and SchedulingCalendarContext for project/activity/relationship-lag scopes.
  - Added CalendarResolverRegistry; requested calendar versions never silently fall back to another version.
  - Added portability fields for activity-calendar and relationship-lag-calendar policies.
  - Added regression tests for inheritance, explicit lag calendar, version isolation and invalid kinds.
  - Existing CPM date semantics remain unchanged until the time-aware Forward/Backward integration gate is complete.
  - Runtime CI remains unverified.

- 33.4.29 Activity Calendar & Relationship-Lag Calendar Resolution: implemented.
  - Added versioned CalendarReference and SchedulingCalendarContext.
  - Activity calendar explicitly falls back to the project calendar only through Shared Core rules.
  - Relationship-lag calendar is independently addressable and otherwise follows the effective activity calendar.
  - CalendarResolverRegistry rejects missing versions instead of silently substituting another calendar.
  - Project portability schema now carries versioned calendar assignment references.
  - Web/Desktop/Mobile must consume these references through Shared Core and must not implement local calendar selection semantics.
  - Time-aware CPM integration remains the next gate; runtime CI execution remains unverified.

- 33.4.30 Time-Aware Forward Pass Integration: first real time-based CPM path implemented in Shared Core.
  - Added TimeActivity, TimeRelationship and TimeScheduledActivity.
  - Added time_forward_pass using versioned activity and relationship-lag calendar context.
  - Implemented exact datetime FS/SS/FF/SF boundary semantics for working-hour duration and non-negative working-hour lag.
  - Explicitly rejects implicit working-day/hour conversion and negative working-hour lag until inverse semantics are separately certified.
  - Added regression tests in tests/scheduling/test_time_forward_pass.py.
  - Web/Desktop/Mobile remain consumers of Shared Core; no client scheduling logic is introduced.
  - Runtime CI execution remains unverified.

- 33.4.30 Time-Aware Forward Pass Integration: implemented.
  - Added/updated the executable time-aware Forward Pass path using explicit TimeActivity, TimeRelationship, TimeQuantity and LagQuantity contracts.
  - FS/SS/FF/SF are supported with working-hour positive, zero and negative lag through the authoritative lag calendar.
  - Negative lag uses inverse working-time arithmetic; no elapsed-clock approximation is used.
  - Time-aware finish boundaries use half-open working intervals, so an FS-zero successor normalizes through breaks/non-working periods correctly.
  - Added SF and negative-lag regression coverage.
  - Date-based Forward Pass remains unchanged for compatibility.
  - Remaining gates: time-aware Backward Pass/Float, constraints, schedule options/criticality parity, portability round-trip tests and CI verification.

- 33.4.30 Time-Aware Forward Pass Integration: implemented.
  - Added Shared Core time_forward_pass using TimeActivity/TimeRelationship and explicit calendar contexts.
  - Integrated working-hour duration and signed working-hour lag with FS/SS/FF/SF semantics.
  - Added exact inverse working-hour arithmetic and preserved interval-end boundaries without microsecond drift.
  - Added regression coverage for negative lag and SF/FF inverse behavior.
  - No implicit working-day-to-hour conversion was introduced.
  - Remaining gates: time-aware Backward Pass, Float/Critical Path, constraints, portability completion, cross-client contracts, and final P6 time-based parity pack.
  - Runtime CI remains unverified.

- 33.4.31 Time-Aware Backward Pass + Float: implemented.
  - Added time_backward_pass, calculate_time_floats and time_schedule.
  - Supports FS/SS/FF/SF with signed working-hour lag in inverse propagation.
  - Total Float is measured in working hours; negative float is preserved and critical under zero threshold.
  - Free Float is relationship-aware and uses the authoritative successor-side lag calendar.
  - Added regression tests for terminal finish, FS inverse, negative lag, zero float and positive float.
  - Remaining gates: time-aware constraints, richer schedule options, full portability/client contract pack, and final P6 time-based parity certification.
  - Runtime CI remains unverified.

- 33.4.32 Time-Aware Constraints + Schedule Options: implemented.
  - Added six datetime-based P6-aligned constraints in Shared Core.
  - No Earlier Than affects early dates only; No Later Than governs late bounds; Mandatory Start/Finish apply to both early and late dates.
  - Constraint targets are normalized through the authoritative activity working-time calendar.
  - Added Forward/Backward integration and regression coverage.
  - Schedule mode remains an explicit application-level contract; no client-specific constraint logic was introduced.
  - Remaining gates: formal time-aware schedule-options contract, complete portability for per-activity time data/constraints, cross-client API regression pack, and final P6 time-based parity certification.
  - Runtime CI remains unverified.

- 33.4.33 Time-Aware Client Integration & Portability Contract: implemented. Portable calculation context now carries time scheduling options and datetime constraints; Web/Desktop/Mobile parity rules are documented; Shared Core remains authoritative. Remaining gates are typed API DTOs, cross-client parity fixtures, offline portability round-trip tests, and final P6 time-aware parity review. Runtime CI remains unverified.

- 33.4.34 Typed Time-Aware API Contract v1: `shared/contracts/time-scheduling.schema.json` defines portable calculation context, activities, relationships, duration/lag units, calendar references, and exact Decimal-like wire representations. Contract regression tests added. Remaining gates: cross-client parity fixtures, offline portability round-trip tests, final P6 time-aware parity review. Runtime CI remains unverified.

- 33.4.35 Deterministic Client Parity + Offline Round-Trip Foundation: canonical time-scheduling payload serialization and SHA-256 fingerprint added; cross-client property-order parity and JSON offline round-trip regression tests added. Remaining: scheduling-result parity fixtures against the Shared Core, client adapter/API integration tests, and final P6 time-aware parity review. Runtime CI remains unverified.

- 33.4.36 Time-Aware P6 Parity Certification Gate: certification scope and evidence pack established. Cross-client result-parity fixtures now execute the same Shared Core scheduler repeatedly and compare typed outputs. Stage 33.4 is not marked 100% until full CI execution is verified and any runtime regressions are resolved.

- 33.4.33 Time-Aware Scheduling Portability + Backend Contract: implemented.
  - Added versioned `time-scheduling-portability.v1` backend transport contract.
  - Carries project schema version, explicit activity/relationship-lag calendar assignments, time-aware activity durations, signed relationship lag/lead, and activity constraints.
  - Duration/lag values are validated as canonical Decimal strings; calendar identity requires an explicit positive version.
  - Added regression tests and architecture documentation.
  - Web/Desktop/Mobile remain consumers of the shared contract; no client scheduling formulas were introduced.
  - Merged in PR #54, merge SHA `148e3ceba218d401d21ffc800d6ce93a0ac07b11`.
  - Runtime CI execution remains unverified.


- 33.4.37 CI Regression Execution Gate: **completed — runtime-verified 2026-09-24**.
  - GitHub Actions ConstructionPM CI run **36072663120** completed successfully for commit `170b1f92c2aa1a30fd89f3c3262f0e3710403e8e`.
  - The full pytest suite passed on Python 3.11, 3.12 and 3.13 after resolving the application-gateway delegate contract regression.
  - The follow-up Client Typecheck run **36072663128** also completed successfully.
  - The CI gate is now runtime-verified; no further 33.4.37 work is pending.


- 33.4.38 Contract/CI Hardening: implemented.
  - Added CI regression workflow for Python 3.11–3.13.
  - Added integration coverage ensuring all shared JSON contract files parse as JSON objects and declare schema/title metadata.
  - Added an explicit regression check for the versioned time-scheduling contract identity.
  - GitHub Actions full-suite execution is now runtime-verified by ConstructionPM CI run **36072663120**; the prior 99% verification hold is cleared.

- 33.4.37 Typed Time-Aware API Contract Regression: implemented and merged in PR #55 (SHA `5b8c1b2bdb1743ed841d1c6d1cc4081afc64fb95`). Added a typed versioned API payload for calculation context, time durations, FS/SS/FF/SF lag/lead, and the six datetime constraint DTOs; JSON schema and regression tests updated. No scheduling formulas or client UI logic changed. Runtime CI remains unverified.

- 33.4.38 Cross-Client Offline Regression Pack: implemented and merged in PR #56 (SHA `539b76a86abb4e3f87a4233a69e7eca733c76b88`). Added Web/Desktop/Mobile typed DTO parity regression and InMemory/SQLite offline round-trip coverage for ProjectContext, expected revision, idempotency identity and retry metadata. No scheduling formulas changed. Runtime CI remains unverified.


- 33.4.42 Shared Client Foundation: implemented.
  - Added typed ProjectContext with tenant/project/revision semantics.
  - Added stable ClientError model for cross-client error/conflict presentation.
  - Added first-class Web/Desktop/Mobile ClientKind and explicit Shared-Core capability authority.
  - Added integration tests covering context, client identity, calculation authority and stable error actions.
  - No scheduling, calendar, Progress/EVM, Resource/Cost or financial calculation was duplicated in client models.

- 33.4.39 Time API ↔ Shared Schema Validation Parity: implemented and merged in PR #57 (SHA `d430e60d6b91f8faf24347a896e9809130698163`). API adapter now validates schedule mode, ISO-8601 datetime targets, canonical Decimal duration/lag values, calendar references, relationship types and all six constraint types consistently with the shared JSON schema. Regression tests added. No scheduling calculations changed. Runtime CI remains unverified.

- 33.4.43 Web Client Foundation: implemented.
  - Added strict TypeScript configuration and package boundary under `apps/web`.
  - Added framework-neutral typed API transport with ProjectContext propagation.
  - Preserves stable API errors and optional Idempotency-Key handling.
  - No client-side scheduling/P6, calendar, Progress/EVM, Resource/Cost or financial calculations introduced.

- 33.4.44 Web Runtime Context & Error Boundary: implemented.
  - Added runtime ProjectContext store with tenant/project/revision validation and revision updates.
  - Added framework-neutral stable error/conflict presentation boundary preserving server action semantics.
  - Added integration boundary tests confirming Web does not host calculation engines.

- 33.4.45 Desktop Client Foundation: implemented.
  - Added standalone Desktop package/typecheck boundary.
  - Added explicit offline/online project runtime with revision continuity.
  - Documented Desktop as an installed first-class client independent of Web/Internet for approved core workflows.
  - Added foundation tests.
  - Desktop does not duplicate Shared Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial calculations.

- 33.4.46 Mobile Client Foundation: implemented.
  - Added first-class Mobile package/typecheck boundary.
  - Added explicit offline/online project runtime with revision continuity.
  - Documented Mobile as a field-oriented client using Shared Core semantics.
  - Added foundation tests.
  - Mobile does not duplicate Shared Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial calculations.

- 33.4.47 Offline Mutation Queue & Synchronization Foundation: implemented.
  - Added shared typed OfflineMutation envelope with tenant/project/revision/idempotency identity.
  - Added deterministic FIFO OfflineMutationQueue with duplicate protection and acknowledgement.
  - Added integration tests for queue invariants.
  - Defined synchronization authority and boundaries; durable storage, transport, retry and conflict workflow remain subsequent stages.

- 33.4.48 Durable Offline Storage: implemented.
  - Added framework-neutral OfflineMutationStore protocol.
  - Added in-memory reference adapter for tests.
  - Added portable JSON-file persistence adapter with atomic replacement.
  - Added restart/persistence and acknowledgement integration tests.
  - Storage remains free of Scheduling/P6, Calendar, Progress/EVM, Resource/Cost and financial calculations.

- 33.4.49 Synchronization Transport & Retry Contract: implemented.
  - Added typed sync dispositions: acknowledged/retry/conflict/rejected.
  - Added framework-neutral SyncTransport boundary.
  - Added bounded deterministic exponential RetryPolicy.
  - Preserved idempotency key and expected revision across retries.
  - Added integration tests and architecture contract.

- 33.4.50 Application API Synchronization Adapter: implemented.
  - Added ApplicationMutationGateway and ApplicationSyncAdapter.
  - Added deterministic SyncRunner over durable pending mutations.
  - Only ACKNOWLEDGED removes a mutation; RETRY/CONFLICT/REJECTED remain pending.
  - Added mutation identity verification and integration tests.

- 33.4.41 Client Sync Canonical Export: merged PR #60 (SHA `bec1ab1edf765896b4cc53a65698d168c9612a7d`). Removed the package-level overwrite of the canonical OfflineMutation with the legacy module family while preserving existing sync runner/transport exports; added regression coverage. No scheduling formulas changed. CI verification pending.

- 33.4.51 Concrete API Sync Transport & Server Idempotency: implemented.
  - Added versioned sync-mutation and sync-outcome JSON contracts.
  - Added JSON HTTP transport boundary with context and Idempotency-Key headers.
  - Added server-side reference idempotency store and replay gateway.
  - Rejects reuse of an idempotency key for a different mutation fingerprint.
  - Added integration tests.
  - Production HTTP framework wiring, durable server idempotency persistence, authentication/authorization and end-to-end network testing remain open.

- 33.4.52 Conflict Resolution Contract: implemented.
  - Added shared ConflictContext and ConflictPresentation models.
  - Added versioned sync-conflict.v1 schema.
  - Preserved stable error code, expected/actual revision, available actions and opaque details.
  - Added explicit stale-revision action semantics: discard, refresh_and_retry, defer.
  - Clients only present conflicts; authoritative refresh/retry and business reconciliation remain Application/Shared Core responsibilities.

- 33.4.53 Cross-Client Conflict Presentation Adapters: implemented.
  - Shared framework-neutral adapter for Web/Desktop/Mobile.
  - Preserves stable error code, action semantics and revision context.
  - Client-specific UI remains presentation-only.
  - Added cross-client parity integration tests.

- 33.4.54 End-to-End Conflict Synchronization Flow: implemented.
  - Added explicit Offline Mutation -> Transport -> Conflict boundary.
  - Preserves mutation identity, expected revision and idempotency identity.
  - CONFLICT requires refresh; ACKNOWLEDGED does not.
  - Added integration tests; production network execution remains a later gate.

- 33.4.53 Resource Application Error Contract Hardening: merged PR #61 (SHA `b27d2f8b34a8fc5d32c680d6a8108178c014bd32`). ApplicationError now initializes stable category/code/message/retryable fields and preserves the existing DTO/factory contract; regression coverage added. CI had exposed this backend issue. No Scheduling/P6 semantics changed.

- 33.4.55 Durable Server Sync State Boundary: implemented.
  - Added persistence protocols for idempotency and conflict state.
  - Preserved tenant/project scoping and idempotency fingerprint semantics.
  - Extended sync-conflict.v1 with mutation identity, idempotency key and operation.
  - Current stores are deterministic in-memory references; production database durability remains a later integration gate.

- 33.4.56 Database Persistence for Sync State: implemented.
  - Added SQLite persistence for idempotency records and conflict state.
  - Added round-trip and idempotency-key-reuse tests.
  - Preserved tenant/project isolation and Shared Core boundaries.
  - PostgreSQL, migrations, concurrency and production deployment remain later gates.

- 33.4.57 PostgreSQL-Compatible Persistence Contract: implemented.
  - Added framework-neutral SyncStatePersistence contract.
  - Added TransactionManager boundary for atomic Application-layer operations.
  - Documented database-native idempotency uniqueness and concurrency semantics.
  - Live PostgreSQL adapter and concurrent integration tests remain later production gates.

- 33.4.54 Resource Assignment Optimistic Lock Hardening: merged PR #63 (SHA `0aee6b16942e687d7bde91e2b4881b6f4868838a`). Stale assignment writes now raise the existing `OptimisticLockError` contract, matching resource writes; regression coverage added. No Scheduling/P6 semantics changed.

- 33.4.58 PostgreSQL Persistence Adapter: implemented.
  - Added PostgreSQL-specific adapter with database-enforced unique keys.
  - Added parameterized-SQL contract tests.
  - No live PostgreSQL server or concurrent DB execution is claimed yet.

- 33.4.59 PostgreSQL Transaction and Concurrency Gate: implemented.
  - Added PostgreSQL transaction manager with commit/rollback semantics.
  - Added deterministic parallel concurrency harness.
  - Live PostgreSQL execution and true race-condition verification remain a production CI gate.

- 33.4.60 Live PostgreSQL CI Integration: workflow and opt-in live connectivity test added.
  - PostgreSQL 16 CI service is provisioned for integration workflow.
  - Actual GitHub Actions success is not yet verified, so runtime stage remains pending verification.

- 33.4.61 Real PostgreSQL Sync-State Integration: workflows and live tests added.
  - Tests real sync_idempotency round-trip and concurrent same-key requests.
  - Actual GitHub Actions success is not yet verified; runtime completion remains pending.

- 33.4.55 Backend Contract Regression Hardening: merged PR #64 (SHA `7e995c2b7baed8b2a1aaff71457b8a16b630a458`). Fixed `OptimisticLockError` message construction, corrected typed time API required-value return, and fixed SQLite offline queue transaction ownership for enqueue/remove/retry. Regression coverage added. No Scheduling/P6 formulas changed.

- 33.4.62 Persistent Sync Gateway Integration: implemented.
  - Added persistence-backed gateway lookup/replay/store flow.
  - Duplicate identical mutations replay persisted outcomes without delegate re-execution.
  - Key reuse with different fingerprint remains rejected.
  - Full atomic lookup/execute/store transaction hardening remains a subsequent gate.

- 33.4.63 Atomic Sync Transaction & Crash-Safety: implemented.
  - Added transaction-coordinated sync execution.
  - Added commit/rollback tests for success and delegate failure.
  - Database crash recovery and distributed transaction guarantees remain deployment-specific.

- 33.4.64 Atomic Conflict Persistence: implemented.
  - Added explicit conflict persistence integration point.
  - Preserved mutation identity, revision context, stable error code and actions.
  - Full database atomicity between outcome and conflict rows remains the next integration gate.

- 33.4.56 Backend CI Contract Regression Pack: merged PR #66 (SHA `69d3b0885812b688dc9a49b1e7b57b7edddeedaa`). Fixed offline retry transaction ownership, typed decimal time API validation, tenant/project/key-scoped sync idempotency records and stable reuse errors, missing-assignment error mapping, and resource migration schema version. No Scheduling/P6 calculations changed.


- 33.4.65 Final Time-Aware P6 Certification & CI Runtime Gate: **completed — 100%**.
  - Verified GitHub Actions workflow run 35995754604 for commit c79dbb4c7126d8a0e0342ad69dbeec35f569b1b1.
  - Python 3.11, 3.12 and 3.13 all completed successfully.
  - Runtime result: **338 passed, 2 skipped, 0 failed**.
  - The regression run confirms the repaired Shared Scheduling/Core baseline, including calendar interval arithmetic, FS/SS/FF/SF relationships, lag/lead boundaries, Forward/Backward scheduling, float/constraints, typed resource/API contracts, synchronization/idempotency and cross-client regression coverage.
  - Stage 33.4.36 time-aware P6 certification evidence is now runtime-verified. This remains an engineering compatibility gate, not an Oracle certification claim.
  - Stage 33.4 is now eligible to close; future work proceeds to the next product/platform stage without reopening completed 33.4 work unless a new regression is introduced.


### Stage 33.4.61 — Real PostgreSQL Sync-State Integration
Status: **100% — runtime-verified 2026-09-24**
- Live PostgreSQL 16 CI verifies real sync_idempotency round-trip and concurrent same-key uniqueness behavior.
- GitHub Actions run **36054570230** completed successfully for the PostgreSQL sync-state workflow.
- The follow-up live atomic-conflict gate also passed in the same workflow, covering real conflict persistence and idempotent replay.
- No Scheduling/P6 or Shared Calculation Core semantics changed.

### Stage 33.4.64 — Atomic Conflict Persistence
Status: **100% — implemented; runtime-verified 2026-09-24**
- Conflict persistence is executed through the atomic sync executor outcome hook inside the same transaction boundary as idempotency outcome persistence.
- Regression coverage verifies conflict persistence and idempotent replay behavior.
- GitHub Actions run **36054112830** completed successfully for the follow-up conflict-persistence test correction.
- No Scheduling/P6, Progress/EVM, Resource/Cost or Shared Calculation Core semantics changed.


### Stage 33.3.4 — Authorization Boundary
Status: **100% — runtime-verified 2026-09-24**
- Added framework/provider-neutral Application authorization policy at `src/construction_pm/application/authorization.py`.
- Carries tenant_id, project_id and user_id with effective roles for every project-scoped authorization decision.
- Added explicit permissions: project.read, project.write, project.schedule and project.admin.
- Initial baseline roles: viewer, planner and project_admin.
- Authentication provider concerns remain outside Shared Domain/Calculation Core.
- Added integration regression tests for allow/deny behavior, stable AuthorizationError and context preservation.
- No Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar or financial calculation semantics changed.
- GitHub Actions run **36054570225** completed successfully on Python 3.11, 3.12 and 3.13, covering the authorization integration regression suite.
- Authorization allow/deny matrix, stable errors and tenant/project/user context preservation are runtime-verified.
- Next documented gate: Stage 33.3.6 API revision propagation and optimistic-locking contract.


### Latest Stage 33.4 Runtime Verification
- Commit `87354c31b19b4db007cc0149280912aaeb233130` corrected the zero-duration subtraction boundary expectation after CI identified the resolver's authoritative normalization behavior.
- GitHub Actions run `36053309326` completed successfully on Python 3.11, 3.12 and 3.13.
- Runtime result: **355 passed, 2 skipped, 0 failed**.
- This verification supersedes the earlier unverified runtime notes for the time-aware calendar/scheduling regression path.
- Stage 33.4 remains closed for engineering work unless a new regression is introduced; subsequent work should proceed to the next product/platform stage.

### Latest Sync/Conflict Runtime Verification
- Commit `dad3b10789f3a09e6615be0aa045b63bc583d65d` completes the atomic conflict persistence test correction.
- GitHub Actions run `36054112830` completed successfully.
- The atomic conflict persistence regression pack is now runtime-verified; subsequent work can proceed to the next sync production gate.

### Stage 33.4.66 — Cross-Client Parity Regression Gate
Status: **100% — runtime-verified 2026-09-25**
- Added `docs/architecture/CLIENT_INTEGRATION_GAP_MATRIX.md` defining the Web/Desktop/Mobile integration boundary and Shared Core calculation authority.
- Added cross-client regression coverage for shared ProjectContext identity/revision and Scheduling/Progress-EVM/Resource-Cost capability authority.
- Offline capability remains client-specific while calculation semantics remain Shared Core-owned.
- GitHub Actions run **36056263616** completed successfully on Python 3.11, 3.12 and 3.13.
- PostgreSQL Sync State workflow run **36056263748** also completed successfully.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.


### Stage 33.4.68 — Shared Client API Sync Transport Boundary
Status: **100% — runtime-verified 2026-09-25**
- Added `apps/client-sync/src/api-sync-transport.ts` as the TypeScript bridge from `ClientSyncRunner` to the existing versioned `/api/v1/sync/mutations` application/API boundary.
- Preserves tenant/project context, expected revision and idempotency key without duplicating business calculations.
- Maps retryable API errors to `RETRY` and non-retryable API errors to `REJECTED`; validates successful mutation identity.
- Added transport and runner regression tests, including generic API test doubles required by strict TypeScript typechecking.
- GitHub Actions Client Typecheck run **36060255053** completed successfully, covering Web, Desktop, Mobile and client-sync.
- ConstructionPM CI run **36060255327** completed successfully.
- PostgreSQL Sync State workflow run **36060254941** completed successfully.
- Latest verified implementation commit: `7f44c75c911433ef3bb3d347c08b2678c45d5115`.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
- Next gate: add end-to-end client sync outcome regression coverage for `ACK / RETRY / CONFLICT / REJECTED` across the shared runner and versioned application/API boundary.

### Stage 33.4.67 — Shared Offline Mutation Queue Client Gate
Status: **100% — runtime-verified 2026-09-25**
- Added the shared TypeScript `apps/client-sync` queue consumed by Desktop and Mobile foundations.
- Queue enforces `sync-mutation.v1`, preserves ProjectContext/expected revision and rejects cross-mutation idempotency-key reuse.
- Only `sync-outcome.v1` with disposition `acknowledged` removes a queued mutation; retry/conflict/rejected outcomes remain pending.
- Added `ClientSyncRunner` with deterministic FIFO submission, mutation-identity validation and stop-on-non-acknowledged semantics.
- Added Client Typecheck workflow covering client-sync, Web, Desktop and Mobile.
- GitHub Actions run **36058894403** completed successfully for Client Typecheck, including all four client typechecks and the client-sync runtime tests.
- ConstructionPM CI run **36058894354** completed successfully.
- PostgreSQL Sync State workflow run **36058894216** completed successfully.
- Latest verified commit: `a55c322f2fe23a280e33d2db0552d841f6a1d83c`.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
- Next gate: connect the shared queue to the existing versioned transport/application synchronization boundary and add end-to-end client sync outcome regression coverage.
### Stage 33.4.69 — End-to-End Client Sync Outcome Regression
Status: **100% — runtime-verified 2026-09-25**
- Added end-to-end TypeScript regression coverage from `ClientSyncRunner` through `ApiSyncTransport` and the versioned API boundary.
- Verified `ACK`, `RETRY`, `CONFLICT` and `REJECTED` outcomes with the queue retaining or removing mutations according to the shared sync contract.
- Client Typecheck run **36060519167** completed successfully.
- ConstructionPM CI run **36060519137** completed successfully.
- PostgreSQL Sync State workflow run **36060519320** completed successfully.
- Latest verified commit: `f8e11714cb5a1ff7bee1782eab0d6b96ee194553`.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
- Next gate: validate conflict/revision behavior against the real application/API mutation boundary and ensure Web/Desktop/Mobile runtime adapters consume the same versioned outcome contract.

### Stage 33.4.70 — Authoritative Conflict Revision Refresh & Cross-Client Retry Boundary
Status: **implemented — runtime verification pending**
- Web/Desktop/Mobile stale-revision retry paths now refresh the authoritative project revision through the shared sync-project-revision.v1 contract before rotating the mutation idempotency key and retrying.
- Client retry paths no longer accept a caller-supplied guessed revision for STALE_REVISION.
- Added VersionedSyncRevisionEndpoint at the application/API boundary and an end-to-end regression covering CONFLICT -> authoritative revision refresh -> retry -> ACKNOWLEDGED.
- Web/Desktop/Mobile regression tests verify the server-provided revision is used, including a non-sequential revision jump, and that retry metadata follows the refreshed revision.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
- Runtime CI verification remains pending; recent GitHub Actions runs have failed without executable steps/logs, so those statuses are not interpreted as code-test failures.


### Stage 33.4.71 — PostgreSQL Atomic Idempotency Execution Lock
Status: **implemented — runtime verification pending**
- PostgreSQL idempotency execution now acquires a transaction-scoped advisory lock derived from tenant/project/idempotency key before the delegate executes.
- This closes the concurrency gap where two transactions could both observe a missing idempotency record and execute the mutation side effect before the unique-key insert.
- PostgreSQL persistence retains the database unique key and race-safe insert semantics; the advisory lock protects the delegate execution itself.
- Added a live PostgreSQL concurrency regression requiring the same mutation key to execute the delegate exactly once across independent database connections.
- Added a live PostgreSQL concurrency regression proving distinct idempotency keys can execute delegates concurrently, confirming lock granularity is scoped to tenant/project/key.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.
- Runtime CI verification remains pending; the latest GitHub Actions status is not yet reported for these commits.


### Stage 34.2 — P0 Contract & Portfolio Control
Status: **current implementation track through 34.2.14 completed/merged; documentation reconciliation in progress**

- 34.2.2 — Backend P0 persistence: implemented and verified.
- 34.2.4 — P0 resource envelope: implemented and verified.
- 34.2.5 — Field operations core/sync bridge: implemented and verified.
- 34.2.6 — Field assurance/core persistence and PostgreSQL atomicity: implemented and live-verified.
- 34.2.7 — Change/Claim core + Client Integration Audit: implemented; Client resource sync boundary coverage merged in PR #149; post-merge CI green.
- 34.2.8 — Procurement/Commercial core: implemented.
- 34.2.9 — Portfolio Control read model: implemented and regression-verified.
- 34.2.10 — Portfolio Decision & Approval Boundary: implemented and merged; Python and client runtime verification completed.
- 34.2.11 — Portfolio Action Transition Boundary: implemented and integrated.
- 34.2.12 — Portfolio Action Persistence: implemented and integrated.
- 34.2.13 — Portfolio Action Audit & Revision Transition Boundary: implemented and integrated.
- 34.2.14 — Portfolio Action Transition Integrity: implemented, live PostgreSQL verified, and merged.

Boundary rule: Portfolio Control remains a cross-project read/decision layer and does not duplicate authoritative Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial calculations. Portfolio decisions/actions do not directly execute project mutations; application/API authorization and mutation boundaries remain authoritative.

### Stage 34.3 — Web/Site Experience: Control Room + Field Foundations
Status: **~90% — runtime-verified implementation track through 2026-09-27**
- PR #248 — Main Workspace WBS/Activity Grid/Gantt rendering: merged; CI runtime-verified.
- PR #249 — versioned `workspace-control-room.v1` snapshot contract and Web runtime-test gate: merged; CI runtime-verified.
- PR #252 — Web projection of existing `control-intelligence-result.v1`: merged; CI runtime-verified.
- PR #253 — Control Summary rendering with authoritative metrics/findings: merged; CI runtime-verified.
- PR #255 — `field-daily-log.v1` Web projection and Daily Log rendering: merged; CI runtime-verified.
- PR #256 — `field-timecard.v1` and `equipment-status-report.v1` Web projections and Control Room panels: merged; CI runtime-verified.
- PR #259 — `field-issue.v1` Web projection and issue panel: merged; Client Typecheck + ConstructionPM CI runtime-verified.
- PR #261 — Inspection / Quality-NCR / Safety Observation / Punch-Closeout Web projections and Field Assurance Control Room: merged; Client Typecheck + ConstructionPM CI runtime-verified.
- PR #262 — versioned `workspace-control-room-read.v1` Web + Backend read integration: merged; Client Typecheck + ConstructionPM CI runtime-verified.
- PR #264 — Change Notice / Change Case / Claim / Change-Claim Impact Web workflow and additive read-envelope hydration: merged; Client Typecheck + ConstructionPM CI runtime-verified.
- PR #271 — Document revision boundary correction: merged; Client Typecheck + ConstructionPM CI runtime-verified.
- PR #280 — Document/RFI/Submittal application/API boundary: merged; runtime-verified.
- PR #281 — Procurement RFQ/Quote/Bid Comparison/PO/Commitment/Delivery Web workflow: merged; Client Typecheck + ConstructionPM CI runtime-verified.
- PR #283 — approval-safe AI Smart Guide + `schedule-query.v1` request composer: merged; Client Typecheck + ConstructionPM CI runtime-verified.
- Web remains presentation/state-only; authoritative Scheduling/P6, Calendar, Progress/EVM, Resource/Cost and financial semantics stay outside the client.
- AI proposals remain traceable and approval-aware; no client-side consequential action execution is permitted.

### Stage 34.3 remaining gates
- Voice interaction / speech-to-command UX against versioned query/action contracts.
- Cross-client parity for the expanded Control Room workflows.
- Final Stage 34.3 integration/regression gate and runtime evidence reconciliation.

Percentage note: the ~90% figure is an engineering workflow estimate based on completed Stage 34.3 gates; it is not a claim of commercial product completeness or market superiority.

### 2026-09-27 — Backend Continuation Reconciliation After PR #273
Status: **verified baseline / documentation reconciled**
- Current main baseline at this reconciliation: `1b1ffe040fba36b557cbfaabff9407472d106384`.
- PR #273 (Field Assurance authoritative write guard) is merged; its exact head passed ConstructionPM CI run `36306525146` and Client Typecheck run `36306525137`.
- Stage 33.4.72–33.4.73 atomic idempotency execution hardening is already runtime-verified through PR #171, including live PostgreSQL same-key serialization and distinct-key concurrency.
- Job-Step Transaction & Replay Boundary is already runtime-verified through PR #206, covering success, failure/rollback, retry, replay, key reuse, optimistic-lock conflict and same-key concurrency.
- Existing API/Web-readiness regression coverage verifies ProjectContext/tenant-project isolation, revision/optimistic locking, idempotency, authorization, typed DTOs, transaction rollback and the authoritative Field Assurance write guard.
- No duplicate implementation of those completed gates is authorized.
- Current Stage 34.3 remaining gates are voice interaction/speech-to-command UX, cross-client parity, and final integration/runtime evidence reconciliation. Document/RFI/Submittal and Procurement/Commercial slices are already implemented and runtime-verified through PRs #280 and #281; AI Smart Guide/schedule-query request composition is implemented and runtime-verified through PR #283. Current Backend/Application/API inspection found no concrete missing Hasan-owned boundary for the remaining voice/parity gates; provider-specific ASR/TTS and presentation remain client/provider-adapter work under `VOICE_INTERACTION_BOUNDARY.md`.
- For Hasan's backend track, do not create a duplicate backend boundary for the remaining client/provider-owned gates. Implement backend work only if a concrete authoritative contract/application/persistence gap is demonstrated.

### 2026-09-27 — Document/RFI/Submittal Application/API Boundary
Status: **100% — runtime-verified through PR #280**
- Added `DocumentApplicationService` for tenant/project-scoped document create/read/update/status-transition orchestration.
- Existing `p0-document-resource` contract remains authoritative for contract, drawing, correspondence, RFI, Submittal, delay-claim and evidence resources.
- Existing document persistence remains responsible for idempotent create, expected-revision update, append-only audit and lifecycle persistence.
- Application transactions now wrap document mutations; authorization and actor identity remain at the Application boundary.
- Added thin `DocumentAPI` adapter using the existing `api-error.v1` contract.
- Focused integration coverage includes RFI create/read, Submittal approval, cross-scope/permission rejection, stale-revision conflict and idempotency-key reuse.
- PR #280 exact head `3fe0881c9efcc6af1cf2ac2ca548d385338dd204` passed Python 3.11, 3.12, 3.13 and all Web/Desktop/Mobile/Client-Sync typechecks.
- Merge commit: `cac86817e52b25f956d6366940f76dda5a61ded2`.
- No Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial calculation semantics changed.

### 2026-09-27 — Procurement/Commercial workspace read materialization
Status: **runtime-verified through PR #286**
- PR #286 materialized the existing authoritative Procurement RFQ/Quote/Bid Comparison/PO/Commitment/Delivery records into the versioned `workspace-control-room-read.v1` snapshot.
- The integration uses scoped `BackendP0Repository.list_records` access and enforces tenant/project scope plus the requested project revision.
- Existing typed Procurement contracts and decimal values remain authoritative; no duplicate persistence, procurement calculation, pricing, financial formula, or ERP adapter was introduced.
- Focused backend coverage verifies authoritative materialization and tenant/project isolation.
- PR #286 exact head `8c5b26a6baca9856f577dec4aa08bbdf91368dc8` passed ConstructionPM CI run `36307286970` (Python 3.11/3.12/3.13) and Client Typecheck run `36307286973`.
- Merge commit: `754621dbf2b3da01657e8a920fa500d1556ff8a2`.
- Current main after subsequent repository activity: `1b1ffe040fba36b557cbfaabff9407472d106384`.

### 2026-09-27 — Schedule Query Application/API Boundary
Status: **runtime-verified through PR #295**
- Added the missing Hasan-owned backend Application/API boundary for the existing Core `schedule-query.v1` and `schedule-query-result.v1` contracts.
- The boundary enforces tenant/project authorization and exact query/result scope and revision identity.
- Query evaluation remains delegated to an injected provider; no Scheduling/P6, calendar, Progress/EVM, Resource/Cost or financial calculation was added to API/persistence.
- Source-backed answers and approval-aware proposed actions are preserved in the versioned result envelope.
- PR #295 exact head `7ee2f6a99d053e560284310b9c63b967b4e26341` passed ConstructionPM CI run `36307602845` (Python 3.11/3.12/3.13) and Client Typecheck run `36307602866`.
- Merge commit: `f008f4d20b797b7fc8c7fbe4b9af37fd96d9716d`.


### 2026-09-27 — Roadmap Reconciliation: Stage 86
Status: **100% — implemented, merged and runtime-verified**

- Stage 86 — Language Pack Integrity Verification is implemented on current `main`.
- Language-pack artifacts are verified with SHA-256 before signature acceptance.
- Checksum mismatch blocks signature verification.
- Signature verification is an injected trust-boundary adapter; no private key or signing policy is embedded in the client.
- Regression coverage verifies valid checksum, checksum mismatch, checksum-before-signature ordering, invalid signature rejection and successful checksum+signature acceptance.
- PR #172 was merged to `main` with merge commit `cc10886d7f6fd8794e7632b9d9b86778232ff48d`.
- Exact implementation head `c1c81119a1f68061c7f2548efd617e525a81c8ec` passed ConstructionPM CI run **36296632796** and Client Typecheck run **36296632820**.
- Activation, rollback, key rotation and revocation remain separate lifecycle concerns; existing activation/lifecycle code is not counted as part of the Stage 86 integrity boundary.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics changed.

### Current Roadmap Reconciliation Result
- The repository already contains implemented and merged Stage 84, Stage 85 and Stage 86 multilingual/language-pack boundaries.
- Stage 87 strict language-pack manifest runtime validation is implemented and merged through PR #314 with merge commit `d7c5e8231ab3b25b3c283ee8901b068577fa25c7`. Exact implementation head `cec20048e0eed2f80043d39ef85f5ebc460ac508` passed Client Typecheck `36342222863` and ConstructionPM CI `36342222381`.
- Therefore the next numbered stage must **not be invented from assumption**. The next implementation target requires a new approved roadmap gate based on the existing product completeness program and current architecture/competitive-gap evidence.
- Stage 35 hardening PR #306 is already merged and must not be reopened unless a new regression is demonstrated.

### Stage 34.4 — Shared Control Room Offline/Read-Cache Parity
Status: **100% — implemented, merged and runtime-verified 2026-09-27**

- PR #311 merged the Stage 34.4 workspace read-cache/runtime boundary onto current main at merge commit `3ca05d011dfc457f1b45be500b5ebfcb00531cd1`.
- The implementation provides the versioned `workspace-control-room-cache.v1` contract, shared Client-Sync cache adapter, Web cached-read projection, and Desktop/Mobile workspace-read integration.
- Runtime coverage verifies tenant/project/revision isolation, immutable snapshots, stale detection, authoritative online refresh, offline last-known behavior, revision-mismatch rejection, and cross-client shared-adapter behavior.
- Exact implementation-head verification recorded for PR #311:
  - Client Typecheck run `36340776620`
  - ConstructionPM CI run `36340776628`
- PR #313 was a redundant later reconciliation attempt and was closed without merge; no work from it is required for the Stage 34.4 completion record.
- Subsequent main commits only advanced CI workflow configuration; current main at this reconciliation is `7ea399bbc62a8b6737be06ab837944852ffabfb2`.
- No client-side Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics were introduced.



### 2026-09-27 — Dependency Graph API Application/API Boundary
Status: **100% — merged and runtime-verified through PR #328**
- Added the missing Hasan-owned versioned `dependency-graph.v1` API adapter over the existing Dependency Graph Application/Persistence boundaries.
- The API validates the transport contract version and timezone-aware audit timestamp, preserves tenant/project scope and distinct project `revision` versus `graph_revision`, and delegates authorization, idempotency, transaction and revision semantics to the Application boundary.
- Added focused integration coverage for the versioned envelope, unsupported contract version, audit timestamp validation, and distinct revision fields.
- PR #328 exact implementation head `05df8d1d7a6f237cad61514321ff3c336f51db05` passed ConstructionPM CI run `36346154172` and Client Typecheck run `36346154198`.
- Merge commit: `93af2ca34e3143d0e8a1bb456645c4b3282c61b1`.
- Stale PR #326 was superseded and closed; no duplicate implementation is required.
- No Scheduling/P6, Calendar/Duration, Progress/EVM, Resource/Cost or financial calculation semantics were moved into API/persistence/client layers.

### Current Backend Continuation Point
- Re-read `HASAN_NEXT_STEPS.md` and current `main` before the next implementation.
- Inspect open PRs and current contracts/application/persistence state to identify the first concrete missing Hasan-owned boundary.
- For remaining Stage 34.3 voice/presentation and cross-client parity gates, do not add a backend duplicate when the missing work belongs to client/provider adapters under `VOICE_INTERACTION_BOUNDARY.md`.
- Do not invent a new numbered stage without an approved roadmap gate.


### 2026-09-27 — Dependency Graph API Revision Provenance
Status: **100% — merged and runtime-verified through PR #331**
- Corrected the concrete API gap left by PR #328: `source_revision` and `target_revision` are now carried through the versioned request/application/persistence path and returned in the API envelope.
- Added focused validation for non-negative source/target revisions and regression coverage proving both fields survive the API boundary.
- PR #331 exact implementation head `869e17ae406a5d5e03257c47fe3786202678f31d` passed ConstructionPM CI run `36346728936` and Client Typecheck run `36346728879`.
- Merge commit: `0c713bac98e1ec3939c0368bd77941b578865103`.
- This was a targeted correction of a demonstrated gap; stale PR #222 was not revived wholesale.


### 2026-09-27 — Stage 34.3 Cross-Client Voice Adapter Parity
Status: **runtime-verified through PR #334**
- Added Desktop and Mobile provider-neutral voice adapter wrappers over the existing shared voice boundary.
- Both clients delegate voice-command normalization, tenant/project/revision scope validation and output-capability checks to the shared client-sync contract.
- PR #334 exact implementation head `3e58a0c1744ad92fa6a8a62d68b78741cb567f72` passed Client Typecheck run **36347809502** and ConstructionPM CI run **36347809550**.
- Merge commit: `3942d9fd2df466e8c9c09157a80a0b979b12b9da`.
- The cross-client parity gate is therefore runtime-verified. Remaining Stage 34.3 work is provider-specific voice UX/integration and final integration/regression evidence reconciliation.
- No Scheduling/P6, Progress/EVM, Resource/Cost or financial calculation semantics were introduced.
