# Stage 33.4 Sync Outcome Contract

Date: 2026-09-24

## Purpose

Define the backend/client result boundary for online, retried and offline mutations without duplicating business logic in clients.

## Contract

Version: `client-sync-outcome.v1`

Statuses:
- `applied`: mutation was newly accepted and applied.
- `replayed`: an existing idempotent mutation was safely replayed.
- `conflict`: the mutation could not be applied because a conflict such as stale revision must be resolved.
- `rejected`: the mutation was rejected by validation or another stable application boundary.

Successful outcomes may carry the resulting revision. Conflict/rejected outcomes carry a stable error code and may indicate retryability.

This contract does not define scheduling, P6, Progress/EVM, Resource/Cost, or UI semantics.
