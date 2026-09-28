# P6 Financial Period Persistence v1

This boundary persists P6 financial-period metadata by tenant, project and immutable project revision. It does not calculate financial values, periods, earned value, costs, calendars or schedule dates.

The repository supports deterministic reads, scope isolation, revision conflict detection and immutable replay. Application writes/reads execute inside the caller-owned transaction manager. SQLite and PostgreSQL adapters share the same persistence contract.

Financial-period semantics and calculations remain authoritative to the applicable Shared Core/domain contract. This backend slice only stores and retrieves typed project metadata needed by P6 import/export and API layers.

PostgreSQL integration coverage verifies round-trip, tenant/project isolation, stale-revision rejection and transaction rollback.