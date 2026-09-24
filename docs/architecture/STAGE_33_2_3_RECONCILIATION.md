# Stage 33.2.3 — Transaction + Context Reconciliation

## Reconciled baseline

The application transaction boundary and explicit ProjectContext must coexist at the same application boundary.

Rules:
1. Every resource use case receives an explicit ProjectContext.
2. Repository calls are scoped by that ProjectContext.
3. Multi-step application use cases execute inside the TransactionManager boundary.
4. Transaction management does not redefine Scheduling/P6, Progress/EVM, or domain calculation semantics.
5. Context isolation and transaction ownership remain independent concerns: context determines *where* a use case operates; the transaction determines *atomicity*.
6. The NoOpTransactionManager is test infrastructure only; production persistence adapters must provide real atomicity.

## Reconciliation result

This branch is based on the current main lineage after Stage 33.2.2 context isolation. It restores the missing context/transaction modules on that lineage and updates the repository protocol and in-memory adapter to require ProjectContext.

## Regression requirements

- Cross-project and cross-tenant resource/assignment isolation.
- Application use cases invoke repository operations with the active ProjectContext.
- Transaction exceptions propagate without hidden commits.
- API DTOs continue to serialize calculated Decimal values as canonical strings.
