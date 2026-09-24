# Stage 33.2.6 — Cross-Module Regression Suite

## Objective
Protect the shared calculation and integration contracts across Scheduling, Progress/EVM, Resource/Cost, Reporting, API contracts and project portability.

## Regression invariants
1. Shared contracts are versioned and discoverable under `shared/contracts/`.
2. Project portability preserves calendar/version and calculation context.
3. Resource/Cost numeric unit values crossing the API remain canonical decimal strings.
4. API DTOs serialize calculated values by invoking authoritative Domain methods.
5. No client may introduce an alternative scheduling, progress, EVM, resource or cost formula.
6. Integration tests verify contracts rather than UI-specific implementations.

## Scope
This suite is intentionally contract-focused. Existing module-specific unit tests remain authoritative for detailed domain behavior; this suite catches cross-module drift and typed-contract regressions.

## Completion gate
Stage 33.2 is complete only when the integration contracts, portability contract, regression coverage and current-main lineage have been reviewed and reconciled.
