# Stage 33.3.4 — Durable SQLite Idempotency Storage

## Status

**100% — durable adapter, schema migration, and regression tests implemented.**

## Scope

- SQLite persistence for mutation idempotency records.
- Records are scoped by tenant/company/project, operation, and idempotency key.
- Fingerprint mismatch returns stable `IDEMPOTENCY_KEY_REUSE` conflict.
- First execution records the key in the same SQLite transaction as the mutation.
- Failed mutations roll back their idempotency record.
- Replays use the application-provided replay callback and do not execute the mutation again.
- Resource schema advances from v3 to v4 and the portable infrastructure schema is updated.

## Transaction rule

The durable idempotency adapter participates in the same SQLite connection and transaction as the application mutation. This prevents a successful idempotency record from surviving a failed mutation. SQLite transactions do not nest with `BEGIN`; the adapter therefore detects an existing transaction and lets the existing owner control commit/rollback.

## Next

Stage 33.3.5: authorization boundary and API revision propagation.
