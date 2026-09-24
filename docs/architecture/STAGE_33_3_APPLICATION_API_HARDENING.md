# Stage 33.3 — Production Application/API Hardening

## Objective
Harden the Application/API boundary for real Web and Desktop clients while preserving the Shared Domain/Calculation Core as the only authoritative calculation source.

## Mandatory invariants
1. Application services own use-case orchestration and transaction boundaries.
2. Repositories own persistence mechanics and never redefine domain calculations.
3. API adapters serialize versioned typed contracts; they never calculate scheduling, progress, EVM, resource, cost, or duration semantics independently.
4. ProjectContext is mandatory for project-scoped application operations.
5. Optimistic-locking revisions are preserved across Application → Repository → API round trips.
6. Domain-calculated Decimal values remain canonical decimal strings at API boundaries.
7. API errors use stable typed error categories rather than leaking database/framework exceptions.
8. Idempotency is required for externally retried mutation operations where duplicate submission could create duplicate business effects.
9. Authentication/authorization checks belong at the application/API boundary; domain calculations remain independent of the authentication mechanism.
10. Web and Desktop consume the same API contracts and business semantics.
11. Audit/revision records remain append-only where required by finalized project rules.
12. Integration tests cover success, validation failure, stale revision, context isolation, transaction failure and typed serialization.

## Work sequence
### 33.3.1 — Application/API contract audit
Inventory all current resource/application/API boundaries and identify missing context, typed fields, error handling and revision propagation.

### 33.3.2 — Stable error contract
Define versioned machine-readable error categories for validation, context, conflict/stale revision, authorization and persistence failures.

### 33.3.3 — Mutation idempotency contract
Define idempotency keys and replay behavior for API mutations that may be retried by Web/Desktop clients.

### 33.3.4 — Authorization boundary
Define application-level permission checks without coupling Shared Domain/Calculation Core to authentication providers.

### 33.3.5 — Integration regression
Add API/Application tests covering the contracts above and ensure existing P6/Scheduling, Progress/EVM and resource calculation tests remain unchanged.

## Completion gate
Stage 33.3 is complete only when the application/API contracts, error semantics, idempotency policy, authorization boundary and regression tests are documented and integrated on current main.
