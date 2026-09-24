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
Status: **82% — in progress; Stage 33.4.26 parity regression pack added 2026-09-24**
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
- 33.4 Offline Mutation Queue Retry Attempt: implemented and merged in PR #49 (2026-09-24); retry attempts are persistent and transaction-aware, while mutation identity/fingerprint remains stable.
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
