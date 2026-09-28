# P6 Resource Assignment Persistence Boundary v1

## Scope

This boundary persists P6 Activity Resource Assignment records for the Hasan-owned Backend/Database/Application/API track.

Each record is scoped by tenant, project, project revision, assignment identity, activity and resource. Optional role, units, actual/remaining units, cost snapshots, unit/currency metadata, calendar reference and note metadata are preserved as typed persistence data.

## Semantics boundary

This boundary does not calculate resource demand, rates, costs, calendars, leveling, scheduling or financial results. Shared Core remains authoritative for Resource/Cost and Calendar semantics. The repository stores values supplied by an authoritative application/domain boundary.

## Persistence invariants

- assignment identity is immutable within (tenant_id, project_id);
- identical replay is idempotent;
- a changed definition is rejected with IMMUTABLE_RESOURCE_ASSIGNMENT;
- a mismatched project revision is rejected with REVISION_CONFLICT;
- tenant/project scope is isolated;
- Decimal values are persisted without float conversion;
- reads are deterministic by assignment id;
- application services own the transaction boundary.

SQLite and PostgreSQL implementations expose the same repository contract.

## Verification

Focused tests cover round-trip and deterministic ordering, activity/resource filtering, tenant/project isolation, stale revision rejection, immutable replay semantics, Decimal preservation and fail-closed validation. Live PostgreSQL coverage additionally verifies rollback and typed Decimal round trips.

## Explicit non-goals

No P6 scheduling, calendar, resource-rate, leveling, cost calculation or financial-period calculation semantics are introduced.
