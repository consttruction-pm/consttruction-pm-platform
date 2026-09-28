# P6 Report/Profile Field Mapping Persistence v1

## Purpose

Persist the backend metadata required for P6 report/profile field selections without making the backend a report renderer or redefining P6 field semantics.

Each mapping is scoped by tenant, project and project revision. A mapping identity is immutable for `(tenant_id, project_id, profile_id, field_id)`.

## Stored metadata

- profile identifier and display name;
- authoritative subject-area identifier;
- canonical field identifier;
- deterministic ordinal;
- exportability flag;
- optional label override;
- explicit string metadata for forward-compatible provider/profile information.

Unknown metadata is retained in `metadata_json`; it is never silently discarded.

## Boundary

This slice does not implement report rendering, spreadsheet generation, layout calculation, field semantics, scheduling, calendar, duration, progress/EVM, resource/cost or financial calculations.

Clients and report/print UX remain consumers of the persisted metadata. Shared Core remains authoritative for P6 field meaning.

## Consistency

- tenant/project isolation is enforced by repository keys;
- stale project revisions fail with `REVISION_CONFLICT`;
- identical retries are idempotent;
- changed definitions at the same immutable identity fail with `IMMUTABLE_REPORT_PROFILE_MAPPING`;
- application operations own the transaction boundary;
- SQLite and PostgreSQL repositories expose the same contract;
- list order is deterministic by ordinal then field identifier.

## Verification

Focused tests cover round-trip persistence, deterministic ordering, scope isolation, stale-revision rejection, idempotent replay, immutability and fail-closed validation. PostgreSQL live verification is required before merge.
