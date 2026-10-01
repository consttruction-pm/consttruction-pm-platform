# P6 Resource Assignment Period Write API v1

## Purpose

`p6-resource-write-api.v1` provides the Backend/Application write boundary for already-defined, time-phased ResourceAssignment period values.

It persists authoritative data through the existing `P6ResourceAssignmentPeriodApplicationService`. It does not calculate resource spread, calendars, leveling, CPM, float, duration, or cost.

## Operation

- `save_assignment_period(value, auth_context)`

The operation requires a `BackendScope(tenant_id, project_id, project_revision)` matching the authorization context and `project.write` permission.

## Data contract

The response preserves:

- assignment/activity/resource identifiers;
- period start identifier;
- Decimal units and cost;
- tenant/project/project revision scope;
- explicit contract version `p6-resource-write-api.v1`.

## Persistence behavior

The existing repository remains authoritative for:

- deterministic replay of identical values;
- immutable conflict rejection for changed values;
- stale revision rejection;
- PostgreSQL concurrency safety.

The write API does not introduce another persistence store or another resource model.

## Ownership boundary

Jalal/Shared Core owns the semantics that determine time-phased resource demand and calendar-aware behavior. Hasan owns this persistence/application/API seam. Consumers must use the authoritative API rather than reading database tables directly.

## Verification

Focused tests cover typed round-trip, Decimal preservation, authorization/scope enforcement, immutable replay behavior, and revision conflict propagation.
