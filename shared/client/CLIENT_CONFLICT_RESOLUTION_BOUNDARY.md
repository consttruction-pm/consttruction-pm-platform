# Client Conflict Resolution Boundary

## Scope

A client may present and resolve a synchronization conflict, but it must not invent an authoritative calculation or silently overwrite a newer revision.

## Conflict input

When client-sync-outcome.v1 returns status = conflict, the client has:

- the queued mutation and its original ProjectContext;
- the original idempotency key;
- the original expected revision;
- the authoritative conflict error_code;
- the retryable flag when supplied.

The client must preserve this information for the user's resolution flow.

## Allowed resolution actions

1. **Discard** — remove the queued mutation after explicit user confirmation.
2. **Refresh and retry** — obtain the current authoritative project state, let the user review/edit the intended change, then submit a new mutation with a new idempotency key and the current expected revision.
3. **Defer** — keep the conflict visible and do not silently retry it.

A client must not:

- change expected_revision merely to bypass a conflict;
- reuse an idempotency key for a materially different mutation;
- calculate a replacement schedule, cost, Progress, or calendar result locally;
- silently replace authoritative server state;
- treat the conflict message text as a stable programmatic discriminator.

## Revision rule

Only an authoritative applied or replayed outcome may advance the active client session revision. A conflict never advances it.

## Platform parity

Web, Desktop, and Mobile may present the conflict differently, but the underlying resolution semantics above are shared and must remain equivalent.
