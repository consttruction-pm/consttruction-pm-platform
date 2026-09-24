# Resource/Cost Client Mutation Outcome Fixture

This fixture closes the Resource/Cost mutation lifecycle at the client boundary.

## Applied

```json
{
  "contract_version": "client-sync-outcome.v1",
  "status": "applied",
  "operation": "create_assignment",
  "revision": 9,
  "error_code": null,
  "retryable": false,
  "idempotency_key": "idem-resource-assignment-001"
}
```

The client removes the queued mutation and advances its ProjectContext session to revision 9.

## Replayed

A replayed outcome with the same idempotency key is treated as successful and authoritative. The client removes the queued mutation and accepts the authoritative revision; it does not execute the mutation again locally.

## Conflict / rejected

Conflict and rejected outcomes remain explicit non-success states. The client preserves the queued mutation for the existing conflict/defer workflow and does not advance the session revision.

## Parity rule

Web, Desktop, and Mobile adapters must normalize these outcomes with identical semantic status, operation, idempotency identity, revision, error code, and retryability. Presentation and localization may differ; mutation semantics may not.
