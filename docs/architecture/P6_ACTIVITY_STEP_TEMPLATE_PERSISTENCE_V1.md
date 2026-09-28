# P6 Activity Step Template Persistence Boundary v1

Effective date: 2026-09-28.

## Scope

This boundary persists the P6 Activity Step Template metadata surface identified by the P6 parity inventory.

Stored data:
- tenant/project/project-revision scope;
- immutable template identity;
- template name and description;
- explicit string metadata for UDF/context keys.

## Deliberate non-goals

This boundary does not apply templates to activities, create or reorder steps, calculate weights/progress, or implement scheduling, calendar/duration, Progress/EVM, Resource/Cost or financial semantics.

If an authoritative Shared Core template contract is introduced, this boundary must be reconciled to that version before behavior is added.

## Consistency

Identity is (tenant_id, project_id, template_id). Stored project_revision must match the requested revision. Identical replay is idempotent, changed definitions are rejected, reads are deterministic by template_id, and the application service owns the transaction boundary.

SQLite and PostgreSQL implementations share the same persistence contract.

## Evidence

Focused tests cover round-trip, deterministic ordering, tenant/project isolation, stale revision rejection, idempotent replay, immutability and fail-closed validation. PostgreSQL integration covers round-trip, scope isolation, revision conflict and rollback when CONSTRUCTION_PM_POSTGRES_DSN is configured.
