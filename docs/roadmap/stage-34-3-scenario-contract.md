# Stage 34.3 — Scenario Contract Boundary

## Scope
The Shared Core scenario boundary is versioned and non-mutating. Scenario requests and proposals are revision-scoped to a tenant/project snapshot and carry auditable source references.

## Contracts
- `shared/contracts/scenario.v1.schema.json` — scenario request/input.
- `shared/contracts/scenario-proposal.v1.schema.json` — scenario output/proposal.
- `src/construction_pm/control_intelligence/scenario.py` — runtime domain enforcement.

## Invariants
- Scenario source evidence must use the same project revision as the request/proposal base scope.
- Scenario changes and impacts cannot silently consume stale evidence.
- A scenario proposal cannot authorize mutation of authoritative project state.
- No P6 scheduling, calendar/duration, Progress/EVM, Resource/Cost, or financial calculation is performed by the scenario contract.

## Backend/application boundary
The Shared Core emits typed scenario inputs/proposals only. Persistence, authorization, transaction boundaries, optimistic locking, and any eventual application of an approved change remain in the application/API/backend ownership boundary. Client layers must not become an authoritative scenario calculation engine.

## Verification
Focused Python regression tests cover request-level source drift, change-level source drift, impact-level source drift, proposal change drift, and the immutable mutation prohibition. Full CI is required before merge.
