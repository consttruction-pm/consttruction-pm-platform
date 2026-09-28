# P6 Baseline Persistence Boundary v1

## Scope

This boundary persists baseline metadata and immutable baseline-to-project-revision identity for the P6 parity track.

It supports:
- tenant/project/project-revision isolation;
- stable baseline identity;
- explicit baseline role: PRIMARY, SECONDARY, TERTIARY or USER_SELECTED;
- source project revision provenance;
- immutable metadata with identical replay idempotency;
- SQLite and PostgreSQL repositories;
- application-owned transaction boundaries;
- deterministic listing.

## Deliberate non-goals

This slice does not define or calculate:
- baseline date/unit/cost comparisons;
- baseline variance calculations;
- primary/secondary/tertiary selection semantics beyond persisted role metadata;
- schedule, calendar, progress/EVM, resource/cost or financial calculations.

Those semantics remain dependent on the authoritative Shared Core contract. The repository stores the metadata needed for a later concrete comparison/selection contract without inventing calculation behavior.

## Concurrency and revision

The persisted identity is (tenant_id, project_id, baseline_id). A write through a different project revision is rejected with REVISION_CONFLICT. Replaying the exact immutable definition is idempotent; changing an existing definition is rejected.

## Evidence

Focused SQLite tests cover round trip, deterministic ordering, scope isolation, stale revision rejection, immutability/idempotency, validation and application transaction ownership.

PostgreSQL integration covers round trip, tenant isolation, stale revision rejection and rollback when CONSTRUCTION_PM_POSTGRES_DSN is configured.
