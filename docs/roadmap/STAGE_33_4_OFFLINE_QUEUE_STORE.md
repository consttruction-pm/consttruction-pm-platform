# Stage 33.4 — Offline Mutation Queue Store

Date: 2026-09-24

## Purpose
Provide a persistence boundary for queued offline mutations without moving business calculations into clients.

## Rules
- The queue stores the existing `offline-mutation.v1` envelope.
- Tenant/company/project context remains part of the storage key.
- Operation + idempotency key prevent duplicate queue entries.
- Queue storage does not execute scheduling, progress, EVM, resource or cost calculations.
- SQLite is an infrastructure adapter; the queue contract remains portable.
- Synchronization/Application code owns conflict resolution and authoritative execution.

## Verification
- In-memory deterministic adapter.
- SQLite round-trip regression.
- Duplicate queue-key regression.
