# P6 Resource Read API v1

## Purpose

`p6-resource-read-api.v1` is the authoritative application/API read boundary for resource assignments, assignment-scoped time-phased values, and resource spread buckets.

It exposes persisted facts already owned by the P6 persistence repositories. It does not calculate resource demand, capacity, leveling, float movement, calendar arithmetic, or costs.

## Scope and authorization

Every operation requires:
- `BackendScope(tenant_id, project_id, project_revision)`;
- an authorization context for the same tenant/project;
- `project.read` permission.

Cross-tenant/project access is rejected before repository access.

## Operations

- `get_assignment(scope, assignment_id)`
- `list_assignments(scope, activity_id?, resource_id?)`
- `get_assignment_period(scope, assignment_id, period_start)`
- `list_assignment_periods(scope, assignment_id?)`
- `get_spread(scope, spread_id, period_id)`
- `list_spreads(scope, spread_id?)`

List operations inherit deterministic ordering from the authoritative repositories.

## Type preservation

DTOs preserve `Decimal` instances for units, costs and spread values rather than converting them to floating point. Date/period identifiers and IDs remain strings. Unit and currency metadata are returned unchanged.

## Shared Core consumption

Jalal's Shared Core may consume these DTOs to construct authoritative `ResourceDemand` / `ResourceCapacity` inputs. The backend must not read persistence tables directly from Shared Core and must not create a second resource model.

Leveling, CPM, float, calendar, duration and cost calculation semantics remain outside this API.

## Revision behavior

The requested project revision is part of the scope. Existing persistence repositories reject stale revisions with their established `REVISION_CONFLICT` contract. The read API does not weaken or translate that behavior.

## Regression evidence

`tests/test_p6_resource_read_api.py` verifies assignment, period and spread round trips, Decimal precision preservation, deterministic ordering, tenant/project scope enforcement, and authorization enforcement.

Live PostgreSQL persistence remains covered by the existing P6 assignment/spread integration tests; this API layer introduces no second database adapter.
