# Stage 33.3.1 — Application/API Contract Audit

Date: 2026-09-24

## Audit result

The current main branch was audited at the Application → Repository → API boundary.

### Confirmed
- ResourceApplicationService already owns use-case orchestration and receives a ProjectContext and TransactionManager.
- ResourceRepository now has an explicit ProjectContext on every project-scoped operation.
- InMemoryResourceRepository enforces context validation and isolates tenant/company/project data.
- Resource API serializes Decimal-like values as canonical decimal strings.
- normalized_remaining_units() is invoked before serialization; a prior bound-method defect is covered by regression tests.
- Transaction boundaries remain in Application for resource mutations.

### Gaps identified for subsequent 33.3.x work
1. SQLiteResourceRepository is not yet context-scoped at the persistence schema/query level. This must be hardened before production multi-tenant use.
2. API DTOs do not yet expose a formal versioned envelope/error contract.
3. Application validation currently raises generic ValueError; stable machine-readable error categories are needed.
4. Mutation idempotency is not yet defined/implemented for retry-sensitive API operations.
5. Authorization is not yet represented as an explicit Application boundary contract.
6. Optimistic-locking revision values are persisted but are not yet consistently represented in the ResourceAssignment API DTO contract.

## 33.3.1 action completed
- Restored the context-scoped ResourceRepository contract on current main.
- Added context-isolation and invalid-context regression coverage.
- Preserved existing calculation semantics; no Scheduling/P6 or Progress/EVM logic was changed.

## Next
Proceed to 33.3.2 Stable Error Contract, while SQLite persistence context hardening remains a required integration item before Stage 33.3 completion.
