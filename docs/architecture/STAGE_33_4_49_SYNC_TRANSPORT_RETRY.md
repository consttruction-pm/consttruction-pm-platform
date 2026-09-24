# Stage 33.4.49 — Synchronization Transport & Retry Contract

## Transport

Clients submit the exact OfflineMutation envelope through a framework-neutral SyncTransport boundary.

The transport does not reinterpret or recalculate the mutation payload.

## Outcomes

A synchronization attempt has one of four dispositions:

- acknowledged
- retry
- conflict
- rejected

Retry outcomes carry an explicit server/transport-provided delay.

## Retry

The reference RetryPolicy uses bounded exponential backoff. It is deterministic and capped. A future scheduler may add jitter at the transport orchestration layer without changing mutation identity or business semantics.

## Idempotency

Every submission retains its original idempotency_key. Retries must reuse the same identity; a retry is never a new mutation.

## Revision

expected_revision remains unchanged across retries. A conflict must be surfaced as a conflict and must not be silently rewritten by the client.

## Authority

Server/Application results remain authoritative. Clients may render and localize outcomes but may not recalculate Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial semantics.

## Remaining work

Concrete API transport, server acknowledgement persistence, conflict UX and end-to-end sync orchestration remain subsequent stages.
