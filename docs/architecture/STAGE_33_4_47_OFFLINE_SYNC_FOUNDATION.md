# Stage 33.4.47 — Offline Mutation Queue & Synchronization Foundation

## Purpose

Provide a shared, deterministic offline mutation envelope and queue for Desktop and Mobile.

## Contract

Every queued mutation preserves:

- tenant_id
- project_id
- expected_revision
- mutation_id
- idempotency_key
- operation
- opaque typed payload

The queue preserves insertion order and rejects duplicate mutation identities and duplicate idempotency keys.

## Authority

The queue does not calculate scheduling, calendar, progress/EVM, resource/cost, or financial semantics. It only transports mutations to the authoritative Application/Shared Core boundary.

## Synchronization rule

A future synchronization adapter must submit the exact queued mutation with its expected revision and idempotency identity. Server outcomes, including stable conflict errors, remain authoritative. Client presentation may localize the outcome but must not recompute the business result.

## Scope

This stage establishes the shared offline queue primitive. Durable local storage, retry policy, network transport, conflict-resolution workflow, and end-to-end synchronization are subsequent stages.
