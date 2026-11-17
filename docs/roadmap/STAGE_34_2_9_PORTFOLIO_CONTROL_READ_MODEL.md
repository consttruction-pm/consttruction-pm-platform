# Stage 34.2.9 — Portfolio Control Read Model

Status: **implementation in progress — canonical PostgreSQL persistence and provider are under active implementation on branch `fix/portfolio-control-provider-owned-implementation`; not merged or runtime-verified.**

## Scope

Provide a cross-project Portfolio Control read model backed by a canonical, tenant-scoped Enterprise portfolio lifecycle/membership source. It preserves authoritative Engineering project revisions and opaque revision-pinned references to existing Schedule, Progress/EVM, Cost, Resource, Risk, Claim and Procurement results. Project status/name and all engineering facts are read from the existing Engineering project lifecycle source; this stage does not calculate them.

## Canonical persistence boundary

The implementation introduces one Enterprise-owned persistence boundary:
- `enterprise_portfolios`: stable tenant-scoped portfolio identity and optimistic portfolio revision.
- `enterprise_portfolio_memberships`: unique tenant/portfolio/project membership, membership state, authoritative project revision, membership revision and opaque source-reference JSON.
- `enterprise_portfolio_audit`: append-only audit events for portfolio creation and membership additions/updates.

The repository is PostgreSQL-backed and transaction-neutral: the caller owns commit/rollback. Portfolio and membership writes use row locks and expected revisions. Duplicate membership is rejected by the primary key. Audit UPDATE/DELETE is rejected by a database trigger.

The provider composes these persisted membership records with read-only project identity/status/revision from `project_lifecycle_projects`. It rejects unknown/cross-tenant portfolios, missing projects, stale Engineering project revisions and source-reference revision mismatches. It derives only the membership-state counts; it does not calculate engineering KPIs.

## Acceptance criteria

- Portfolio snapshots are tenant-scoped and include a stable portfolio id.
- Membership records preserve membership state, portfolio revision, authoritative project revision and source-reference revisions.
- Duplicate projects/memberships are rejected.
- Summary counts are derived only from persisted membership status.
- Result references remain opaque links to authoritative project/domain results; no project calculations are duplicated.
- Source references are mandatory and revision-safe.
- Snapshot identity, timestamp and ordered content are deterministic for the same persisted revision set.
- Read-model code remains independent from Backend P0 project-list adapters.
- Every referenced project is re-authorized by the Enterprise consumer before any snapshot metadata/data is exposed.
- Unit, PostgreSQL live integration and consumer integration tests pass on the exact final SHA before merge.

## Non-goals

- No portfolio analytics/KPI or cross-project financial calculation.
- No new P6 Scheduling, Progress/EVM, Resource/Cost or financial formulas.
- No decision mutation/approval workflow in this stage.
- No use of `PortfolioQueryAdapter.list_projects` as a membership source or fallback.
- No project data duplication: Engineering remains authoritative for project records and calculations.

## Current implementation evidence (not yet accepted)

- `src/construction_pm/portfolio_control_persistence.py`: canonical PostgreSQL repository, optimistic revisions, append-only audit, read-only Engineering project facts adapter and concrete snapshot provider.
- `tests/test_portfolio_control_persistence.py`: provider isolation, authoritative facts, stable identity/time and stale-source coverage.
- `tests/integration/test_portfolio_control_persistence_postgres_live.py`: live PostgreSQL persistence, revision, audit and source freshness coverage.
- Branch base: `326a6ab9a5b36617f7b04e04b13cb329ff0d3a13`.
- Latest implementation commits must be read from the branch head; no CI/runtime pass is claimed until exact-head workflows complete.
