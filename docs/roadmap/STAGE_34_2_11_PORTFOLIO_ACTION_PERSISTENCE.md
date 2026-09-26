# Stage 34.2.11 — Portfolio Control Action Persistence & Audit Ledger

Status: implementation in progress.

## Scope

Persist Portfolio Control Actions at tenant/portfolio scope with optimistic locking, idempotent creation replay, and append-only audit history.

## Acceptance criteria

- Action storage is independent of project-scoped Backend P0 persistence.
- Create is idempotent within tenant + portfolio + idempotency key.
- Reusing a key with a different fingerprint is rejected.
- Idempotent create replay returns the immutable original create result even after later state transitions.
- Action state transitions use an explicit expected action revision.
- Stale action revisions are rejected.
- Audit events are append-only and revisioned.
- Proposal and decision authorization remains in the Application layer.
- Nested transaction boundaries use distinct savepoints.
- Persistence is migration-safe for the initial idempotency result snapshot field.
- No project mutation is executed by the Portfolio Action Store.
