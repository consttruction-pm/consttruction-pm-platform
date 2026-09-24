# Offline Queue and Sync Presentation Boundary

## Purpose

`ClientSyncPresentation` is the framework-neutral state consumed by Web, Desktop, and Mobile while presenting offline mutations and authoritative sync outcomes.

## States

- `queued`: mutation is pending normal sync.
- `applied`: authoritative mutation applied; revision is authoritative.
- `replayed`: authoritative idempotent replay; revision is authoritative.
- `conflict`: mutation remains deferred for explicit resolution.
- `rejected`: mutation remains deferred and requires explicit handling.

## Invariants

- Operation and idempotency identity are preserved.
- Conflict/rejected error codes and retryability come from the authoritative outcome.
- Successful states require the authoritative revision.
- Presentation never calculates schedule, cost, Progress, calendar, or replacement revision values.
- Framework-specific labels and controls may differ, but semantic state and identity must remain equivalent.

## Offline behavior

A conflict or rejected mutation is not silently retried. The queue remains inspectable through explicit resolution actions. A replacement mutation must use the existing conflict-resolution boundary with a fresh idempotency key and authoritative expected revision.
