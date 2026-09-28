# Hasan — Current Continuation / Backend Track

## Current baseline — 2026-09-28

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `main`
- Current verified main head after PR #471: `6762d4d9d03142611dea4e5af2c67161d3e62f8a`.
- PR #468 added scoped P6 code assignments and is merged; do not repeat.
- PR #469 added the code-assignment application transaction boundary and is merged; do not repeat.
- PR #470 made code-assignment upsert atomic on SQLite/PostgreSQL and is merged; do not repeat.
- PR #471 added live PostgreSQL verification for code-assignment persistence. ConstructionPM CI run #2003 and Client Typecheck run #1706 both passed; PR #471 merged as `6762d4d9d03142611dea4e5af2c67161d3e62f8a`.
- The PostgreSQL verification in #471 covers round-trip, scope/revision isolation, immutable metadata and the atomic conflict/replay path from independent connections. It does not claim a simultaneous-write stress test.
- Baseline comparison/variance calculation remains blocked until an authoritative Shared Core snapshot/version contract exists. Backend/API must not invent those semantics.

## P6 status

- P6-2 typed Field Registry/UDF persistence/API is implemented and PostgreSQL-verified through prior merged slices.
- P6-7 interchange codecs and typed round-trip conformance fixtures are implemented and merged.
- P6-8 covered surfaces now include financial periods, resource spreads, codes/code assignments, activity steps, activity period actuals, cost accounts, expenses, resource assignments, baselines and report/profile mappings.
- P6-3 Column/View/Layout remains Javad-owned.
- P6-4 Formula semantics remain Shared Core/Jalal-owned; Hasan may implement only concrete persistence/API dependencies after the authoritative contract is merged.
- P6-9 final conformance/certification remains a cross-team gate.

## Immediate execution rule

1. Re-read this file and `docs/roadmap/STAGE_STATUS.md`.
2. Fetch current `main` and inspect open PRs/issues.
3. Select only the first actually missing Hasan-owned Backend/Database/Application/API/Enterprise Integration boundary.
4. Do not revive stale PRs or duplicate completed P6 surfaces.
5. Add focused tests, PostgreSQL verification where applicable, and documentation with every implementation.
6. Require exact-head GitHub Actions verification before marking a gate complete.
7. Keep Shared Core authoritative for scheduling, calendar/duration, formula, progress/EVM, resource/cost and financial calculation semantics.

## Current next-point rule

After #471 there is no evidence in the current open-PR set of another concrete Hasan-owned P6 implementation ready to start. Before creating another P6 persistence slice, reconcile the remaining Role/Assignment/Document/Issue/Work Product surfaces and any active Shared/Core prerequisites against current `main`. If no authoritative backend gap exists, record the blocker/ownership boundary instead of inventing a feature.
