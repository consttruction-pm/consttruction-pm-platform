# P0 Field Operations — PostgreSQL Persistence Boundary

## Scope

This adapter makes the existing P0 Field Operations contract durable in PostgreSQL without changing its Application/API semantics.

The persisted resources remain tenant- and project-scoped and preserve:

- operation identity and type;
- operation payload and opaque location reference;
- project revision;
- idempotency key and canonical fingerprint;
- append-only audit identity.

## Transaction and concurrency contract

A persist operation:

1. opens the caller-provided transaction boundary;
2. locks the tenant/project revision row with `FOR UPDATE`;
3. checks idempotency before mutation;
4. rejects a reused key with a different fingerprint;
5. rejects a stale project revision;
6. increments the project revision;
7. persists the resource and audit record atomically.

Replay returns the previously persisted resource and does not create another mutation.

## Boundary rules

No scheduling, calendar, duration, Progress/EVM, Resource/Cost or financial calculation is introduced here. Payload and location semantics remain opaque to this persistence adapter.

The adapter is provider-specific infrastructure behind the existing repository contract; it does not select an external field/photo/location vendor.

## Verification

The integration test exercises initialization, project setup, transactional persist/replay, stale revision rejection, idempotency-key reuse rejection, tenant isolation and read round-trip through the adapter.

The next runtime gate is the repository's PostgreSQL CI integration environment.
