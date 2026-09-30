# P0 Procurement / Commercial Boundary

Version: v1

This boundary provides tenant/project-scoped persistence and application semantics for RFQ, quote, bid comparison, purchase order, commitment, and delivery resources.

Invariants:
- Revisions, audit and idempotency are explicit.
- Repository owns persistence mechanics; service owns use-case orchestration.
- Payload values are opaque; no procurement pricing, financial, cost or commitment calculations are implemented here.
- External procurement/ERP providers must remain behind explicit adapters.
- PostgreSQL integration must reuse the existing transaction/idempotency primitives.

PostgreSQL persistence/transaction integration is implemented on current main; remaining work is focused on runtime verification and regression maintenance.


## PostgreSQL persistence
The application boundary now has a PostgreSQL adapter with explicit transaction scope, tenant/project revision locking, idempotency replay/reuse protection, audit persistence and round-trip reconstruction. Procurement pricing, financial formulas, commitment accounting and commercial calculations remain outside this boundary.
