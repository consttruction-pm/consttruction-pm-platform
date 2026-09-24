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

**Next point: Stage 33.2 — cross-module integration and portability checks within Developer 1 backend/database/integration-support scope.**

### Stage 33.2 — Cross-Module Integration & Project Portability
Status: **100% — reconciled and merged into current main**
- Integration/portability contract established.
- Stage 33.2.1 API DTO reconciliation merged (PR #6; merge SHA `f4764248ea4376fb7307f5eb5e566482ce4cb4cc`).
- Stage 33.2.2 explicit tenant/company/project context isolation merged (PR #9; merge SHA `e601ebd15430dcb9555be57ad9d94ec845d3cc03`).
- Stage 33.2.3 application TransactionManager contract reconciled and merged by Hasan (PR #16; merge SHA `200000407d10f105c5e457ab72e677f4d4f9a6df`).
- Stage 33.2.4 versioned typed Resource/ResourceAssignment contracts merged (PR #13; merge SHA `e0b8e72d349a4102858c35c260b6a72f06a4a8b1`).
- Stage 33.2.5 versioned project portability contract merged (PR #14; merge SHA `67eefcc27f322db017c825785508f700cfeb61d4`).
- Stage 33.2.6 cross-module regression suite merged (PR #15; merge SHA `cf3da8d3acfbd258a5b0742991bb5ac905e4da62`).
- Current main lineage was reconciled without wholesale merging the divergent review branch.
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics were redefined.
- PR #17 was superseded by PR #16 and closed to prevent duplicate implementation.

**Stage 33.2 completion gate: 100%.**

### Stage 33.3 — Production Application/API Hardening
Status: **100% — complete**
- 33.3.1 Application/API contract audit: **100%**
- 33.3.2 Stable Error Contract: **100%**
- Stable machine-readable ApplicationError categories implemented.
- Validation, ProjectContext and not-found failures are mapped to stable error codes.
- API serialization preserves category/code/retryable semantics.
- Regression tests added.
- Remaining: SQLite persistence context hardening, mutation idempotency, authorization boundary, revision propagation and final integration regression.
- No Scheduling/P6 or Progress/EVM semantics changed.
- 33.3.3 Mutation Idempotency Contract: **100%**
- Application-level idempotency key + deterministic request fingerprint contract implemented.
- Same key + same fingerprint replays without executing the mutation twice.
- Same key + different fingerprint returns stable `IDEMPOTENCY_KEY_REUSE` conflict.
- Context isolation and regression tests added.
- Durable SQLite idempotency persistence completed in Stage 33.3.4.
- 33.3.4 Durable SQLite idempotency storage: **100%**
- SQLite idempotency records are transactionally coupled to mutation execution.
- Resource schema advanced to v4 and portable schema updated.
- Failure rollback and fingerprint conflict regression tests added.
- 33.3.5 Authorization boundary: **100%**
- Explicit application authorization policy contract added.
- Resource mutations are authorized before persistence.
- Stable forbidden error and regression coverage added.
- 33.3.6 API revision propagation and optimistic-locking contract: **100%**
- Expected revisions propagate from API → Application → Repository.
- Current revisions are exposed at the API boundary.
- Stale writes return stable `STALE_REVISION` conflict errors.
- Shared optimistic-lock error contract and regression tests added.
- 33.3.7 Final cross-layer integration/regression hardening: **100%**
- API, Application, authorization, idempotency, revision and context-isolation contracts covered together.
- Final Resource backend regression suite added.
- **Stage 33.3 completion gate: 100%.**
- Next: Stage 33.4 — Production Web/Desktop Client Foundation and Shared Client Integration.

### Stage 33.4 — Production Web/Desktop/Mobile Client Foundation and Shared Client Integration
Status: **15% — in progress; three-client foundation established 2026-09-24**
- Scope document: `docs/architecture/STAGE_33_4_WEB_DESKTOP_CLIENT_FOUNDATION.md`.
- Web, Desktop and Mobile must consume the same versioned API/Application contracts.
- Shared Domain/Calculation Core remains the single source of Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar and financial calculation semantics.
- Client responsibilities: application shells, navigation/workspace integration, typed contract consumption, localization, Jalali/Gregorian presentation, error/conflict UX, mobile field workflows, offline sync UX and parity testing.
- Hasan/backend responsibilities: API/shared-contract integration support, ProjectContext propagation, authorization/session boundary, optimistic-locking/idempotency/error handling and regression coverage.
- Completion requires cross-client contract, workflow and parity regression tests across Web/Desktop/Mobile.
- No Scheduling/P6 or Progress/EVM semantics are redefined in Stage 33.4.
- 33.4.1 client foundation structure/contracts: **started**.
- 33.4.2 shared typed API client boundary: **backend support complete — versioned Resource contract and stable application-error contract published with regression coverage**.
- 33.4.6 Mobile field client foundation: **scope established**.
- 33.4.7 Mobile security/sync/device boundary: **scope established**.
- Tracking issue: #26.


### Stage 33.4-B — SQLite Transaction Boundary Hardening
Status: **100%**
- Application transaction rollback against SQLite persistence is regression-tested.
- Nested repository transactions participate in the outer application transaction.
- Stable stale-revision error mapping import reconciled.
- No Scheduling/P6, Progress/EVM, or Shared Calculation Core semantics changed.
- Stage 33.4 completion gate: **100%**.
- Next: continue from the next unfinished Stage 33 backend/platform item.
