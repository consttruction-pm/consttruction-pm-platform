# Stage 34.2.9 — Portfolio Control Read Model

Status: implementation in progress.

## Scope

Provide a cross-project Portfolio Control read model that aggregates project identity, membership state, authoritative revision and references to existing Schedule, Progress/EVM, Cost, Resource, Risk, Claim and Procurement results.

## Acceptance criteria

- Portfolio snapshots are tenant-scoped and include a stable portfolio id.
- Project rows preserve authoritative project revision and membership status.
- Duplicate projects in a snapshot are rejected.
- Summary counts are derived only from membership status.
- Result references remain opaque links to authoritative project/domain results; no project calculations are duplicated.
- Source references are mandatory and revision-safe.
- Snapshot generation is deterministic for the same ordered inputs.
- Read-model code remains independent from Backend P0 project persistence.
- Python and client runtime verification is required before merge.

## Non-goals

- No Portfolio CRUD persistence.
- No new P6 Scheduling, Progress/EVM, Resource/Cost or financial formulas.
- No cross-project financial calculations.
- No decision mutation/approval workflow in this stage.
