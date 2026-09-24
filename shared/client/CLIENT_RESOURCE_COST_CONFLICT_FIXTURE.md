# Client Resource/Cost Conflict Fixture

Resource/Cost mutations use the shared client conflict presentation contract. A stale revision must remain an explicit conflict across Web, Desktop, and Mobile.

## Fixture

```json
{
  "contract_version": "client-conflict-presentation.v1",
  "operation": "create_assignment",
  "idempotency_key": "idem-resource-assignment-001",
  "expected_revision": 8,
  "error_code": "STALE_REVISION",
  "retryable": false,
  "available_actions": ["discard", "refresh_and_retry", "defer"]
}
```

## Acceptance

Clients may localize action labels and adapt the interaction layout, but must preserve operation, idempotency identity, expected revision, stable error code, retryability, and action semantics.

A refresh-and-retry flow must obtain an authoritative current revision before creating a replacement mutation, and the replacement must use a fresh idempotency key.

Clients must not recompute Resource/Cost values while resolving the conflict.
