# P6 Cost Account Persistence Boundary v1

## Scope
This boundary persists P6 cost-account definitions and hierarchy metadata. It is tenant/project/project-revision scoped and keeps immutable account identity.

## Contract
- account_id is immutable within a tenant/project.
- name, optional parent account, and description are immutable after creation.
- identical writes are idempotent.
- stale project revisions fail with REVISION_CONFLICT.
- reads are deterministic by account_id.
- self-parent references are rejected.
- PostgreSQL mirrors the SQLite persistence contract.

## Explicit non-goals
This boundary does not calculate costs, rates, resource allocations, financial formulas, earned value, leveling, scheduling or calendar conversions. Shared Core remains authoritative for cost/resource/financial semantics.

Cost-account assignment to activities/resources and interchange mapping remain separate follow-up boundaries and must consume this persisted definition contract.
