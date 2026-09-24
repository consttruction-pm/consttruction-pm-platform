# Backend Idempotency Adapter Parity

Date: 2026-09-24

The in-memory and durable idempotency adapters now expose the same replay contract:
an already-applied mutation requires an explicit replay callback. Neither adapter may
silently return an implementation-specific cached result or execute the mutation again.

This keeps test and production adapters behaviorally aligned and makes
`IDEMPOTENCY_REPLAY_UNAVAILABLE` a stable conflict when a previous result cannot be
reconstructed.

No Scheduling/P6, Progress/EVM or Shared Calculation Core semantics changed.
