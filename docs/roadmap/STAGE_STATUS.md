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
Status: **76% — in progress; schedule-mode/constraint interaction hardened 2026-09-24**
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
- 33.4.20 Backward Constraint Propagation Across FS/SS/FF/SF + Lag/Lead: implemented.
  - Lower-bound Start/Finish constraints now propagate into latest dates instead of being validation-only.
  - Backward results are checked against relationship feasibility after constraint application.
  - Project-finish overflow caused by backward lower-bound constraints is rejected deterministically.
  - Added parameterized tests for all four relationship types and positive/negative lag.
  - Added parameterized coverage for Start No Earlier Than across all four relationship types with positive and negative lag.
  - Added equivalent Finish No Earlier Than coverage across all four relationship types with positive and negative lag.
  - Added mixed relationship networks with different lag signs and downstream constraints.
  - This verifies propagation coverage without duplicating scheduling formulas in clients.
- 33.4.21 P6 Constraint Semantics Matrix: implemented as Shared Core documentation baseline.
- 33.4.22 P6 Constraint Edge-Case Test Pack: implemented.
  - Backward lower-bound constraints now propagate required date movement through successors before final relationship validation.
  - Successor movement remains duration/calendar aware and is rejected if it exceeds project finish.
  - Added FS/SS/FF/SF regression coverage plus project-finish overflow coverage.
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
- Full P6 constraint semantics, exact P6 schedule-option parity, richer time-of-day calendars, and formal P6 parity certification remain pending.
- Full test execution is not marked as verified until CI/GitHub Actions executes the committed test suite.
- Tracking issue: #26.

### Stage 33.4-B — SQLite Transaction Boundary Hardening
Status: **100%**
- Application transaction rollback against SQLite persistence is regression-tested.
- Nested repository transactions participate in the outer application transaction.
- Stable stale-revision error mapping import reconciled.
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics changed.
