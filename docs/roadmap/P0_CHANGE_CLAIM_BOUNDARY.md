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
