# Stage 33.2.3 — Transaction Contract

## Rule
Transaction ownership belongs to the Application/use-case boundary. A repository may expose persistence primitives, but it must not silently redefine atomicity for a multi-step use case.

## Contract
1. One atomic use case owns one explicit transaction boundary.
2. Repository operations participate in the active application transaction.
3. Domain calculations remain transaction-independent and deterministic.
4. Failed multi-step use cases must not leave a partially committed state.
5. Nested repository transactions must not silently commit independently.
6. Real database adapters implement TransactionManager; NoOpTransactionManager is test infrastructure only.
7. Transaction context remains independent from UI, HTTP framework and database vendor.

## Scope
Initial implementation establishes the contract abstraction and test adapter. Concrete database binding follows in persistence integration.