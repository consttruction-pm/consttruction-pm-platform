# P6 Activity Step Persistence Boundary v1

## Scope

This boundary persists the P6 Activity Steps working-data surface required by the P6 parity baseline:
- activity/step identity;
- deterministic sequence;
- description;
- optional typed Decimal weight;
- optional start/finish dates;
- explicit string UDF values for interchange-preservation metadata.

## Ownership

Hasan owns persistence, application transaction ownership and database verification. Shared Core remains authoritative for scheduling, calendar, duration, progress and any calculation semantics. This module does not calculate step progress, activity dates, earned value or schedule results.

## Invariants

- (tenant_id, project_id, step_id) is immutable.
- A write/read against a different project revision fails with REVISION_CONFLICT.
- An identical replay is idempotent.
- A changed definition for an existing step fails with IMMUTABLE_ACTIVITY_STEP.
- Listing is deterministic by activity, sequence and step ID.
- UDF metadata is preserved explicitly rather than silently dropped.
- SQLite and PostgreSQL implement the same repository contract.
- Application operations own their transaction boundary.

## Evidence

Focused SQLite tests cover round-trip, tenant/project isolation, revision conflicts, idempotent replay, immutability and fail-closed validation.

The PostgreSQL integration fixture covers round-trip, scope isolation, rollback and revision conflict when CONSTRUCTION_PM_POSTGRES_DSN is configured.

## Non-goals

No scheduler, calendar, duration conversion, progress/EVM, resource/cost, financial-period calculation, or P6 formula semantics are implemented here.
