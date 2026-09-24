# Stage 33.4.51 — Concrete API Sync Transport & Server Idempotency

## API contract

Offline mutations are submitted through a versioned JSON contract at the Application/API boundary. The reference transport uses:

- `POST /api/v1/sync/mutations`
- `Idempotency-Key`
- `X-Tenant-Id`
- `X-Project-Id`

The mutation body preserves the exact mutation identity, expected revision, operation and opaque payload.

## Server idempotency

Idempotency is scoped by tenant, project and idempotency key. The server stores a fingerprint of the original mutation and its authoritative outcome.

A repeated request with the same identity and equivalent fingerprint replays the stored outcome. Reusing an idempotency key with a different mutation fingerprint is rejected.

## Client behavior

The concrete transport maps the versioned JSON outcome to the shared SyncOutcome type. The client does not reinterpret business results.

## Authority

Server/Application/Shared Core remains authoritative for scheduling, calendar, progress/EVM, resource/cost and financial semantics.

## Scope

This stage provides a reference API transport contract and in-memory server idempotency implementation for deterministic integration testing. Production HTTP framework wiring, durable server-side idempotency persistence, authentication/authorization and end-to-end network testing remain subsequent stages.
