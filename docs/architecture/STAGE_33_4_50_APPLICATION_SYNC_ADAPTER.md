# Stage 33.4.50 — Application API Synchronization Adapter

## Purpose

Connect the durable offline mutation store to the authoritative Application/API boundary without duplicating domain calculations in clients.

## Adapter

ApplicationSyncAdapter delegates each OfflineMutation to an ApplicationMutationGateway and verifies that the returned mutation identity matches the submitted mutation.

## Runner

SyncRunner processes pending mutations in queue order.

- ACKNOWLEDGED: acknowledge/remove the mutation from durable pending storage.
- RETRY: retain the mutation for later retry.
- CONFLICT: retain the mutation for explicit conflict handling.
- REJECTED: retain the mutation for explicit rejection handling.

No disposition other than ACKNOWLEDGED removes a mutation.

## Safety

The runner does not modify expected_revision, idempotency_key, payload, scheduling dates, cost values, progress values, calendar data or any other business semantics.

## Scope

This stage establishes the application synchronization boundary and deterministic one-pass runner. Network authentication, concrete HTTP transport, durable server acknowledgement/idempotency handling, and client conflict UX remain subsequent stages.
