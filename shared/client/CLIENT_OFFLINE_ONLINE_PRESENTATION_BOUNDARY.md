# Client Offline/Online Presentation Boundary

Offline state is a presentation and orchestration concern; it does not create a second business-calculation engine.

## Offline

Clients may:

- display queued mutation count and attempt state;
- show queued, conflict, deferred, applied, and rejected states;
- preserve the original idempotency key and expected revision;
- allow explicit discard, defer, or refresh-and-retry actions;
- show that authoritative data may be stale until synchronization completes.

## Online synchronization

When connectivity returns, clients submit the same versioned mutation contract used online. Applied/replayed outcomes may advance the session revision only from the authoritative response.

Conflict and rejected outcomes remain explicit. They must not be silently retried or treated as successful.

## Prohibited client behavior

Offline clients must not:

- calculate authoritative schedules or dates;
- recalculate Resource/Cost totals or variances;
- calculate Progress/EVM;
- substitute a missing calendar version;
- invent a new revision;
- reuse an old idempotency key for a replacement mutation.

## Cross-client parity

Web, Desktop, and Mobile may render offline state differently, but queue identity, revision semantics, outcome states, and conflict actions remain identical.
