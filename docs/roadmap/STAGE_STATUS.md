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
| Stage 33 — System Integration & Platform Hardening | 35% — in progress |

Progress percentages refer to the documented development workflow, not a claim that production source code for every module already exists.

### Stage 33.4 — Production Web/Desktop/Mobile Client Foundation and Shared Client Integration
Status: **98% — in progress; Stage 33.4.33 time-aware portability contract established 2026-09-24**
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


- 33.4.37 CI Regression Execution Gate: CI workflow added at `.github/workflows/ci.yml`.
  - Runs the full pytest suite on Python 3.11, 3.12 and 3.13 for pushes to main and pull requests targeting main.
  - Installs the project through the declared `.[test]` extra, so the CI environment follows the repository's packaging contract.
  - Stage 33.4 remains 99% until an actual workflow run completes successfully and any failures are reviewed.


- 33.4.38 Contract/CI Hardening: implemented.
  - Added CI regression workflow for Python 3.11–3.13.
  - Added integration coverage ensuring all shared JSON contract files parse as JSON objects and declare schema/title metadata.
  - Added an explicit regression check for the versioned time-scheduling contract identity.
  - Stage 33.4 remains 99% until GitHub Actions produces a successful full-suite run and the resulting test evidence is reviewed.

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
