# Client Integration Progression Map

## Implemented client boundaries

The current client integration foundation covers:

- ProjectContext/session and authoritative revision handling.
- Versioned mutation envelopes with idempotency.
- Stable ApplicationError presentation.
- Offline queue and sync presentation.
- Conflict resolution with discard, refresh-and-retry, and defer.
- Calendar reference/context presentation without local calendar arithmetic.
- Resource/Cost typed DTOs and decimal-string enforcement.
- Resource/Cost mutation workflow and cross-client parity fixtures.

## Next integration gates

Progress, Reporting, WBS/Activity, Gantt, and Dashboard presentation must consume authoritative contracts when their client-facing APIs are available. Client code must not introduce parallel scheduling, Progress/EVM, cost, calendar, or reporting calculations.

For any new shared contract, the implementation must first establish:

1. versioned request/response shape;
2. ProjectContext propagation;
3. optimistic-lock revision semantics;
4. idempotency behavior for retryable mutations;
5. stable error/conflict mapping;
6. cross-client fixture/parity coverage.

## Current repository reality

No dedicated Progress or Reporting client module is currently present under `src/construction_pm`. Therefore this branch does not invent a client DTO or calculation layer for those areas ahead of an authoritative backend contract.

## Completion rule

Each integration section is committed independently and must have a successful client-sync CI run before the next section is treated as complete.
