# Resource/Cost Client Fixture Pack

## Purpose

This fixture pack freezes the semantic payloads that Web, Desktop, and Mobile adapters must interpret identically for Resource/Cost workflows.

## Resource DTO

```json
{
  "contract_version": "resource.v1",
  "id": "R-100",
  "code": "LAB-01",
  "name": "Site Crew",
  "type": "labor",
  "unit": "hr",
  "calendar_id": "CAL-01",
  "active": true,
  "revision": 8
}
```

## Assignment DTO

```json
{
  "contract_version": "resource.v1",
  "activity_id": "A-100",
  "resource_id": "R-100",
  "planned_units": "80.00",
  "actual_units": "32.00",
  "remaining_units": "48.00",
  "planned_cost": "12000.00",
  "actual_cost": "4800.00",
  "remaining_cost": "7200.00",
  "revision": 8
}
```

## Mutation boundary

```json
{
  "contract_version": "client-sync.v1",
  "operation": "create_assignment",
  "context": {
    "tenant_id": "tenant-1",
    "company_id": "company-1",
    "project_id": "project-1"
  },
  "idempotency_key": "idem-resource-assignment-001",
  "expected_revision": 8,
  "mutation": {
    "activity_id": "A-100",
    "resource_id": "R-100"
  }
}
```

## Required parity

- Decimal-like units and costs remain canonical decimal strings.
- Project context, operation, idempotency key, and expected revision are preserved.
- Authoritative revision advances only from an applied/replayed response.
- Conflict/rejected outcomes use the shared stable error and conflict presentation contracts.
- Clients do not recompute units, cost, utilization, variance, rates, or EVM values.
- Platform-specific formatting or localization may change presentation only.

## Acceptance

The same fixture payload must normalize to equivalent semantic DTOs across Web, Desktop, and Mobile adapters. Any platform-specific adapter test that changes mutation identity, revision semantics, decimal representation, or calculation ownership is non-conformant.
