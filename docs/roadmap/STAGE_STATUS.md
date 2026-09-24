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

### Stage 32.8.11 — Resource/Cost ↔ EVM Integration
Status: **100% implementation complete**
- Resource EVM bridge implemented.
- Deterministic Decimal calculations tested.
- Central EVM semantics remain authoritative.

### Stage 32.8.12 — Typed XLSX Import/Export
Status: **100% implementation complete**
- Typed schemas, real XLSX I/O, schema versioning and round-trip test implemented.

### Stage 32.8 — Resource & Cost Control Center
Status: **100%**
- Resource domain, rates, assignments, loading, control, performance, calendars, capacity, overload detection, curves, histogram, EVM bridge, typed XLSX I/O and integration review completed.
- Remaining work is cross-stage/system-level integration outside the Resource & Cost stage.

### Stage 33 — System Integration & Platform Hardening
Status: **35% — in progress**
- Stage 33 is the current implementation area.
- Scope must integrate existing scheduling, progress/EVM, reporting, resource/cost and platform contracts without duplicating domain calculation rules.
- Web-readiness, deterministic calculations, typed data, project portability and API/application/repository boundaries remain mandatory.

### Stage 33.1 — Backend Concurrency Hardening
Status: **100%**
- Resource assignment persistence now has optimistic-locking revision semantics.
- Resource schema version advanced from 2 to 3 with migration-safe assignment revision addition.
- Stale assignment updates are rejected.
- Assignment revision increments are regression-tested.
- Legacy schema migration is regression-tested.
- No Scheduling/P6, Progress/EVM core, or Shared Calculation Core semantics were changed.

### Stage 33.2 — Cross-Module Integration & Project Portability
Status: **100% — reconciled and merged into current main**
- Integration/portability contract established.
- Stage 33.2.1 API DTO reconciliation merged (PR #6).
- Stage 33.2.2 explicit tenant/company/project context isolation merged (PR #9).
- Stage 33.2.3 application TransactionManager contract reconciled and merged by Hasan (PR #16).
- Stage 33.2.4 versioned typed Resource/ResourceAssignment contracts merged (PR #13).
- Stage 33.2.5 versioned project portability contract merged (PR #14).
- Stage 33.2.6 cross-module regression suite merged (PR #15).
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics were redefined.

### Stage 33.3 — Production Application/API Hardening
Status: **100% — complete**
- Application/API contract, stable errors, mutation idempotency, durable SQLite idempotency, authorization, optimistic locking/revision propagation and final cross-layer regression hardening completed.
- No Scheduling/P6 or Progress/EVM semantics changed.

### Stage 33.4 — Production Web/Desktop/Mobile Client Foundation and Shared Client Integration
Status: **45% — in progress; ALAP/Schedule Options foundation added 2026-09-24**
- Scope document: `docs/architecture/STAGE_33_4_WEB_DESKTOP_CLIENT_FOUNDATION.md`.
- Web, Desktop and Mobile consume the same versioned API/Application contracts.
- Shared Domain/Calculation Core remains the single source of Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar and financial calculation semantics.
- No client-specific scheduling formulas are permitted.
- 33.4.8 Portable Shared Scheduling Core foundation: **implemented**.
- 33.4.9 Portable Activity + Forward Pass: **implemented**.
- 33.4.10 Backward Pass + Float Analysis: **implemented**.
- 33.4.11 Foundational Activity Date Constraints: **implemented**.
- 33.4 Offline Project Context backend contract: **implemented** — versioned portable project context with deterministic regression coverage.
- 33.4.12 Backward-Pass Constraint Integration: **implemented**.
  - Late-date calculations now accept the same typed ActivityConstraint set used by Forward Pass.
  - Start/Finish No Later Than constraints cap latest dates; Mandatory Start/Finish constraints enforce exact late dates.
  - Lower-bound constraints remain validated against the resulting late window rather than being silently ignored.
  - Foundational constraint regression tests cover upper bounds, Mandatory Finish, and unknown constraint activity validation.
- 33.4.13 ALAP / Schedule Options foundation: **implemented**.
  - Added typed `ScheduleMode.EARLIEST` and `ScheduleMode.ALAP`.
  - Added `ScheduleOptions` so scheduling mode is explicit and deterministic.
  - ALAP selects the calculated late schedule while preserving early schedule, late schedule and float/critical-path analysis in the result.
  - Default behavior remains EARLIEST/normal CPM output.
  - Added regression tests for ALAP selection and default earliest mode.
- A missing `validate_upper_bound` constraint helper used by Forward Pass was also reconciled into the Shared Core.
- This is still foundational scheduling behavior. Full P6 constraint semantics, exact P6 schedule-option parity, richer time-of-day calendars, and formal P6 parity certification remain pending.
- Full test execution is not marked as verified until CI/GitHub Actions executes the committed test suite.
- Tracking issue: #26.

### Stage 33.4.7 — Sync Outcome Contract
Status: **implemented**
- Versioned typed sync outcome contract added for applied/replayed/conflict/rejected mutation results.
- Revision, stable error code, retryability and idempotency key are represented explicitly.
- Deterministic validation and regression coverage added; no Shared Calculation Core semantics changed.

### Stage 33.4-B — SQLite Transaction Boundary Hardening
Status: **100%**
- Application transaction rollback against SQLite persistence is regression-tested.
- Nested repository transactions participate in the outer application transaction.
- Stable stale-revision error mapping import reconciled.
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics changed.
