# Stage 33.4.28 — Offline Sync Dispatch Contract

Date: 2026-09-24

## Purpose

Define the backend/shared-contract boundary that accepts one queued offline mutation and returns the authoritative typed synchronization outcome.

## Contract

- OfflineMutationTransport.apply() accepts an OfflineMutation.
- The transport must return SyncMutationOutcome.
- OfflineMutationDispatcher validates both request and response.
- The response operation must match the mutation operation.
- The response idempotency key must match the mutation idempotency key.
- Queue lifecycle decisions are intentionally outside this boundary: this contract does not decide whether a conflict/rejection is removed, retried, or resolved by the client workflow.
- No Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar, or financial calculation is performed here.

## Compatibility

- ProjectContext remains carried by OfflineMutation; this boundary does not weaken project/tenant isolation.
- Existing SyncMutationOutcome version remains client-sync-outcome.v1.
- Existing queue identity and retry semantics remain unchanged.
- The contract is transport/application-facing and can be consumed by Web, Desktop and Mobile without duplicating business logic.

## Verification

- Matching operation/idempotency correlation.
- Mismatched operation rejection.
- Mismatched idempotency-key rejection.
- Non-typed transport result rejection.
