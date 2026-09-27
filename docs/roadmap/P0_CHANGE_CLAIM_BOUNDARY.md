# P0 Change / Variation / Notice / Claim Boundary

## Version
v1

## Scope
This boundary persists tenant/project-scoped change, variation, notice, and claim resources with explicit lifecycle status, evidence references, optimistic revisions, append-only audit records, and idempotent mutation behavior.

## Invariants
- Application service owns orchestration and conflict/idempotency behavior.
- Repository owns persistence mechanics.
- Tenant and project scope are part of resource identity.
- Evidence references are opaque; document/OCR/search semantics remain behind their own adapters.
- No scheduling, duration, progress/EVM, resource/cost, or financial calculation is introduced here.
- External providers remain behind explicit adapters.

## Next integration point
Add a PostgreSQL repository/transaction adapter using the existing transaction and idempotency primitives. Do not introduce a second transaction model.


## PostgreSQL persistence
The application boundary now has a PostgreSQL adapter with explicit transaction scope, tenant/project revision locking, idempotency replay/reuse protection, append-only audit rows, and round-trip reconstruction. Pricing, entitlement, schedule, EVM, resource/cost and financial calculations remain outside this boundary.
