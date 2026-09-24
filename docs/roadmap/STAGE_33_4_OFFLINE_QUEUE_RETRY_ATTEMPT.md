# Stage 33.4 — Offline Mutation Queue Retry Attempt

Date: 2026-09-24

## Purpose
Persist retry-attempt metadata for offline mutations without changing mutation identity.

## Rules
- Retry attempts increment from the queued mutation's current attempt.
- `attempt` is retry metadata and is excluded from the mutation fingerprint/idempotency identity.
- Queue identity remains tenant/company/project/operation/idempotency key.
- In-memory and SQLite adapters expose the same retry contract.
- SQLite retry updates participate in an existing transaction and do not commit an outer transaction.
- Missing queued mutations fail deterministically with a stable `KeyError`.
- No business calculation or scheduling semantics are introduced.

## Verification
- In-memory retry increment and identity preservation.
- SQLite retry round-trip and identity preservation.
- Missing-item regression.
- Existing-transaction rollback regression.

## Enqueue idempotency hardening
- SQLite enqueue is idempotent when the existing queue key contains the same mutation fingerprint.
- Reusing the same tenant/company/project/operation/idempotency key for a different mutation is rejected deterministically.
- This keeps SQLite behavior aligned with the in-memory queue and preserves the idempotency contract across offline adapters.
