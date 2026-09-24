# Stage 33.4.57 — PostgreSQL-Compatible Persistence Contract

Sync persistence now has a framework-neutral contract shared by SQLite and future PostgreSQL adapters.

## Contract

The persistence boundary exposes only idempotency and conflict state operations. It does not expose Scheduling/P6 or other business calculations.

## Transaction boundary

A TransactionManager abstraction is defined so Application services can execute sync-state changes atomically without coupling domain logic to SQLite or PostgreSQL APIs.

## Concurrency rule

Idempotency uniqueness must be enforced by the database key `(tenant_id, project_id, idempotency_key)`. A fingerprint mismatch for an existing key remains `IDEMPOTENCY_KEY_REUSE`.

PostgreSQL implementations must preserve these semantics using transactional and database-native uniqueness controls.

## Status

The contract is implemented. A live PostgreSQL adapter and concurrent integration tests remain the next production gate.
