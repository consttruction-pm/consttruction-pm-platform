# Stage 33.2 — Cross-Module Integration & Project Portability Checks

## Objective
Validate and harden the contracts between Scheduling, Progress/EVM, Resource/Cost, Reporting, API/Application/Repository layers, and project portability without introducing duplicate calculation logic.

## Mandatory invariants
1. Shared Domain/Calculation Core remains the single source of truth for calculations.
2. Scheduling/P6 semantics are not reimplemented in Resource/Cost or API layers.
3. Progress/EVM semantics remain authoritative in their existing engines.
4. Resource/Cost may provide typed inputs to EVM but does not redefine EVM semantics.
5. Baseline, Current, Actual and Forecast remain distinct across module boundaries.
6. Calendar context and version travel with project-level calculations.
7. API contracts preserve typed data at the contract boundary; serialization must not alter calculation semantics.
8. Tenant/project context must be explicit at Application/Repository boundaries before production multi-user use.
9. Optimistic-locking revisions must survive repository/application/API round trips for mutable resource assignments.
10. Multi-step application use cases must have explicit transaction boundaries.
11. Project export/import must preserve enough versioned context to reproduce calculations on another device.
12. Integration tests must verify cross-module contracts; unit tests alone are insufficient.

## Current review finding
The existing resource review branch is divergent from current `main` (20 commits ahead and 22 behind at the start of Stage 33.2). Therefore its resource persistence changes must be reconciled against current `main` before integration/merge; the original developer branch must not be treated as already merged.

## Work sequence
### 33.2.1 — Branch reconciliation
- Rebase/merge the approved resource changes onto current main through a dedicated review branch.
- Resolve conflicts without changing shared calculation semantics.
- Preserve the documented assignment revision behavior.

### 33.2.2 — Context isolation contract
- Define the canonical tenant/project context at Application/Repository boundaries.
- Ensure resource reads/writes require the appropriate context.
- Add cross-project isolation regression tests.

### 33.2.3 — Transaction contract
- Identify multi-repository resource/cost use cases.
- Define one application-level transaction boundary per atomic use case.
- Keep repository transaction helpers from silently redefining use-case atomicity.

### 33.2.4 — Typed integration contract
- Verify Decimal, date, duration and Boolean types across Domain → Application → Repository → API.
- Verify API DTOs contain calculated values, not callable/method references.
- Preserve XLSX-compatible numeric/date semantics.

### 33.2.5 — Portability contract
- Verify project export/import carries calendar/version, scheduling settings, calculation settings, resource/cost configuration and schema versions.
- Add a round-trip/reload determinism test using the same project context.

### 33.2.6 — Cross-module regression suite
At minimum cover:
- Resource assignment → cost → EVM bridge.
- Calendar context → time-phased resource values.
- Revision conflict → rejected stale update.
- Project context → no cross-project data leakage.
- Export/import → same calculation context and deterministic result.
- Reporting → consumes authoritative calculated dataset without duplicate formula.

## Developer-1 scope
Hasan owns Backend/Database implementation for the persistence/application/API portions assigned to him. Shared Scheduling, Progress/EVM semantics must not be modified as an incidental dependency. Any cross-module semantic change must first be documented in the Master Reference and explicitly announced to Hasan.

## Completion rule
Stage 33.2 is complete only when the integration contracts and regression coverage are present and the current `main` lineage has been reconciled. A code review branch that is still divergent is not considered integrated.


## 33.2.2 implementation note
A context-scoped SQLite resource persistence adapter now makes tenant/company/project scope explicit for Resource and ResourceAssignment records. Revision checks are enforced per context and invalid context is rejected before database access; the legacy single-context SQLite adapter remains unchanged for compatibility.


## 33.2.3 implementation note
The context-scoped SQLite resource adapter now participates in an application-owned transaction without committing inside an active transaction. Standalone repository calls retain their commit behavior. Integration tests cover atomic rollback across resource and assignment mutations.


## 33.2.4 implementation note
The Resource API v1 boundary now preserves typed rate data without converting domain values to binary floating-point: Decimal rates remain canonical decimal strings, dates remain ISO-8601 date strings, enum values remain stable strings, and Boolean fields remain JSON booleans. The contract schema documents these representations. No scheduling, duration, Progress/EVM, Resource/Cost calculation semantics were reimplemented at the API boundary.


## 33.2.6 implementation note
A cross-module regression suite now covers Resource assignment -> authoritative Resource/Cost -> EVM bridge values, stale assignment revision rejection, project-context isolation, and deterministic project portability reload. The suite consumes existing calculation authorities and does not duplicate scheduling, Progress/EVM, Resource/Cost or financial formulas. Reporting remains an explicit consumer-only boundary.
