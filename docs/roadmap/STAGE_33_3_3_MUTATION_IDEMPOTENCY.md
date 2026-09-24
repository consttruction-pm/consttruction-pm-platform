# Stage 33.3.3 — Mutation Idempotency Contract

## Status

**100% — application contract implemented and regression-tested.**

## Scope

This substage establishes an application-layer idempotency contract for backend mutations without changing Scheduling/P6, Progress/EVM, or Shared Domain/Calculation Core semantics.

### Contract

- A mutation may supply an explicit idempotency key.
- The key is scoped by tenant/company/project context and operation.
- Repeating the same key with the same deterministic request fingerprint replays the original result without executing the mutation again.
- Reusing the same key with a different fingerprint raises stable conflict error `IDEMPOTENCY_KEY_REUSE`.
- Missing/blank keys are rejected when the idempotency store is enabled.
- Mutation failures are not recorded as successful idempotent results.
- The first implementation is an in-memory adapter for deterministic application tests.
- Durable SQLite idempotency storage is intentionally a following persistence substage so the application contract is established first.

## Design boundary

Idempotency is an application orchestration concern. Domain calculations remain unchanged. Repository adapters do not invent idempotency semantics.

## Regression coverage

- replay does not execute the mutation twice;
- key reuse with a different fingerprint is rejected;
- tenant/project contexts are isolated;
- Resource application mutation replay is deterministic;
- request fingerprints are deterministic.

## Next

Stage 33.3.4: durable SQLite idempotency storage and transaction integration.
