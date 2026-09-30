# V1 Full Audit / Coverage Matrix — 2026-09-30

## Baseline

- Repository: `consttruction-pm/consttruction-pm-platform`
- Audit baseline: `main`
- Main SHA: `cd69be63430fc773fd1ed054d8a8c5383ac2b6e7`
- Scope: evidence-backed reconciliation for Issue #459 after current-main inspection.
- Ownership: Jalal = Shared Core/calculation authority; Hasan = PostgreSQL/backend/API/interchange; Javad/Farmj22002 = Web/client UX and integration.

This matrix intentionally uses current `main` as the source of truth. Historical branches and stale PRs are evidence only and are not counted as implemented functionality.

## Open-PR reconciliation

| Item | Current status | Ownership | Audit treatment |
|---|---|---|---|
| PR #517 — FS relationship validation | Open, draft, based on an older main SHA; head `c8c8dfd11a2dcb226f32858293b4b4a670c191b0` | Javad/Farmj22002 | **Not counted**. Scheduling semantics belong to Shared Core; do not merge/rebase as Hasan work. |
| PR #528 — live Web session/project bootstrap | Open; base is older main SHA; head `6701e271c8b79d16889b63a42418c0806667dab9` | Javad/Farmj22002 | **Not counted**. Web/client ownership; requires reconciliation against current main by its owner. |
| PR #416 — PostgreSQL CI path trigger | Closed, not merged | Javad/Farmj22002 | Historical evidence only; no active Hasan implementation dependency established. |

## Active ownership tracks

| Track | Owner | Backend implication | Current treatment |
|---|---|---|---|
| #391 P6 parity / Shared Core | Jalal | Consume authoritative semantics; no duplicate calculation logic | Active prerequisite/semantic authority. |
| #393 P6 persistence/API/import-export | Hasan | PostgreSQL, repository/application/API, typed interchange and DB verification | Active Hasan track. |
| #415 P6 columns/layout UX | Javad/Farmj22002 | Backend only when an authoritative persistence/API gap is demonstrated | Client-owned; do not duplicate UI logic. |

## V1 capability evidence

| Area | Current evidence on main | Hasan-owned status |
|---|---|---|
| Project lifecycle persistence | PR #532 merged; PostgreSQL integration verified | Implemented |
| P6 Field Registry persistence | PR #533 merged; PostgreSQL integration verified | Implemented |
| P6 Mapping Registry API contract identity | PR #535 merged; regression + CI verified | Implemented |
| P6 Field Registry PostgreSQL repository contract | PR #537 merged; PostgreSQL integration, client typecheck and CI verified | Implemented |
| Formula-definition persistence | PostgreSQL repository exists on main | Present; extend only for a concrete contract gap |
| Baseline metadata persistence | PostgreSQL repository exists on main | Present; comparison/variance semantics remain Shared Core-owned |
| Financial-period persistence | PostgreSQL repository exists on main | Present |
| Report-profile persistence | PostgreSQL repository exists on main | Present |
| Typed UDF definition/value persistence | PostgreSQL repositories exist on main | Present |
| XER/XML/XLSX/MS Project interchange | Registry/API direction exists, but full round-trip parity is not evidenced by this reconciliation | **Open parity work** |
| Unsupported-field preservation/rejection | Contract policy exists, but full end-to-end interchange evidence is not established here | **Open verification** |
| Database isolation/revision/concurrency | Existing backend regression/integration coverage plus P6 repository tests | Verify per remaining P6 surface |
| Web navigation / full V1 screen surface | Client-owned; open PRs are stale relative to current main | Not Hasan-owned |

## P6 parity sequence

The authoritative sequence remains:

1. Field Registry.
2. Column/View/Layout engine.
3. Typed UDF/custom field engine.
4. Formula/Calculated Column engine.
5. Full Schedule Options contract/calculation implementation.
6. Full Calendar parity.
7. XER/XML/XLSX/MS Project interchange mapping and round-trip fixtures.
8. P6 conformance regression pack.

Hasan's work must persist/expose Shared Core semantics and must not implement a competing scheduling, calendar or formula engine.

## Evidence rule

A capability is marked implemented only when its current-main implementation and applicable regression/runtime evidence can be identified. A stale branch, old PR, historical chat state, or planned roadmap item is not implementation evidence.

## Immediate continuation

The next Hasan-owned implementation candidate is **not** a new repository simply because P6 has remaining roadmap coverage. First establish a concrete missing API/persistence/interchange boundary on current main. The strongest remaining area identified by this reconciliation is end-to-end P6 interchange round-trip/unsupported-field verification; implementation should begin only after the authoritative mapping contract and existing import/export modules are inspected for a specific missing boundary.

