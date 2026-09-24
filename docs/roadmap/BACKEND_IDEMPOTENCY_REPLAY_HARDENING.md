# Backend Idempotency Replay Hardening

Date: 2026-09-24

The durable idempotency adapter must never execute a business mutation twice for the same
context/operation/idempotency key and fingerprint.

When an existing idempotency record is found, a replay callback is now mandatory. If the
caller cannot reconstruct the prior result, the adapter returns the stable
`IDEMPOTENCY_REPLAY_UNAVAILABLE` conflict instead of invoking the mutation again.

This preserves the project rule that externally retried mutations are idempotent and prevents
a silent duplicate business effect.

Scope: backend/application persistence only. No Scheduling/P6, Progress/EVM or Shared
Calculation Core semantics changed.
