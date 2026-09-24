# Stage 33.4.7 — Backend Sync/Security/Device Boundary

Status: **backend-owned contract support complete**

This substage establishes a platform-neutral mutation envelope for Web/Desktop/Mobile synchronization. It does not implement mobile UI, offline storage, authentication providers, or device-specific workflows.

## Contract guarantees

- All retried/offline mutations carry an explicit `client-sync.v1` contract version.
- `ProjectContext` is explicit in every mutation envelope.
- Every synchronized mutation requires an idempotency key.
- Optional `expected_revision` carries optimistic-locking intent across a reconnect/sync boundary.
- The business mutation remains opaque to the transport envelope; Resource/Scheduling/Progress/EVM semantics stay in their authoritative application/core layers.
- No client writes directly to persistence.

## Ownership boundary

This contract is backend-owned support for Stage 33.4.7. Web/Desktop/Mobile offline queue UX, secure device storage, authentication provider integration, conflict UX, and field workflows remain with the client/product track.

## Regression

`tests/resources/test_client_sync_contract.py` verifies required context, idempotency, revision and mutation fields and rejects an incomplete envelope.

Completion of Stage 33.4.7 still requires the client track's secure device boundary, sync implementation and cross-client synchronization tests.
