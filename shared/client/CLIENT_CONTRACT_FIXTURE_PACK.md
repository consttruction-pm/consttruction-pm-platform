# Client Contract Fixture Pack

## Purpose

This fixture pack freezes the minimum cross-client payload shapes that Web,
Desktop, and Mobile adapters must consume identically.

Fixtures are intentionally framework-neutral. They validate contract shape,
identity propagation, revision handling, and stable outcome categories; they
do not duplicate scheduling, financial, calendar, or Progress calculations.

## Mutation fixture

### Request

```json
{
  "contract_version": "client-sync.v1",
  "operation": "update_activity",
  "context": {
    "tenant_id": "tenant-1",
    "company_id": "company-1",
    "project_id": "project-1"
  },
  "idempotency_key": "idem-activity-001",
  "expected_revision": 7,
  "mutation": {
    "activity_id": "A-100",
    "name": "Foundation"
  }
}
```

Client requirements:
- preserve all three context identifiers;
- preserve the idempotency key across retries/offline replay;
- preserve expected_revision when supplied;
- treat mutation contents as authoritative API input, not locally calculated results.

## Outcome fixtures

### Applied

```json
{
  "contract_version": "client-sync-outcome.v1",
  "status": "applied",
  "operation": "update_activity",
  "revision": 8,
  "idempotency_key": "idem-activity-001"
}
```

### Replayed

```json
{
  "contract_version": "client-sync-outcome.v1",
  "status": "replayed",
  "operation": "update_activity",
  "revision": 8,
  "idempotency_key": "idem-activity-001"
}
```

### Conflict

```json
{
  "contract_version": "client-sync-outcome.v1",
  "status": "conflict",
  "operation": "update_activity",
  "revision": null,
  "error_code": "STALE_REVISION",
  "retryable": false,
  "idempotency_key": "idem-activity-001"
}
```

### Rejected

```json
{
  "contract_version": "client-sync-outcome.v1",
  "status": "rejected",
  "operation": "update_activity",
  "revision": null,
  "error_code": "VALIDATION_ERROR",
  "retryable": false,
  "idempotency_key": "idem-activity-001"
}
```

## Cross-client acceptance rules

Every future client implementation must demonstrate:

1. identical request serialization;
2. identical outcome normalization;
3. no client-owned authoritative calculation;
4. explicit handling of conflict/rejected outcomes;
5. revision updates only from authoritative responses;
6. preservation of idempotency identity across offline/online transitions.

Framework-specific tests may wrap these fixtures, but must not redefine their
semantics.

## Conflict presentation fixture

The conflict fixture must map to the same framework-neutral presentation model in Web, Desktop, and Mobile:

```json
{
  "contract_version": "client-conflict-presentation.v1",
  "operation": "update_activity",
  "idempotency_key": "idem-activity-001",
  "expected_revision": 7,
  "error_code": "STALE_REVISION",
  "retryable": false,
  "available_actions": ["discard", "refresh_and_retry", "defer"]
}
```

Acceptance rule: adapters may localize labels and render controls differently, but they must preserve the action semantics, identity, expected revision, and stable error code. No adapter may recalculate schedule, cost, Progress, or calendar state while presenting the conflict.
