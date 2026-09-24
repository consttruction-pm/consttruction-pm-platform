# Stage 33.4.62 — Persistent Sync Gateway Integration

The synchronization gateway now has a persistence-backed integration boundary.

## Behavior

1. Look up tenant/project/idempotency key.
2. If an identical fingerprint exists, replay the stored outcome without re-executing the delegate.
3. A different fingerprint for the same key is rejected.
4. New mutations execute through the existing application delegate.
5. The resulting outcome is persisted.
6. Conflicts are persisted with stable presentation actions.

## Boundary

Persistence stores sync state; the delegate remains responsible for authoritative application behavior. No Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial calculations are introduced here.

## Concurrency

The persistence/database unique key remains authoritative. Atomic transaction wiring for the full lookup/execute/store sequence is a subsequent hardening gate.
