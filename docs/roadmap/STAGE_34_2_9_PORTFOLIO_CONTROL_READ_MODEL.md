# Stage 34.2.9 — Portfolio Control Read Model

Status: **implemented, merged and runtime-verified through PR #2035.** Production dashboard route mounting remains in ENT-06B #2032.

## Scope

Provide a cross-project Portfolio Control read model backed by a canonical, tenant-scoped Enterprise portfolio lifecycle/membership source. It preserves authoritative Engineering project revisions and opaque revision-pinned references to existing Schedule, Progress/EVM, Cost, Resource, Risk, Claim and Procurement results. Project status and revision are read from the existing Engineering project lifecycle source; this stage does not calculate or duplicate them.

## Canonical persistence boundary

The implementation introduces one Enterprise-owned persistence boundary:
- `enterprise_portfolios`: stable tenant-scoped portfolio identity and optimistic portfolio revision.
- `enterprise_portfolio_memberships`: unique tenant/portfolio/project membership, membership state, authoritative project revision, membership revision and opaque source-reference JSON.
- `enterprise_portfolio_audit`: append-only audit events for portfolio creation and membership additions/updates.

The repository is PostgreSQL-backed and transaction-neutral: the caller owns commit/rollback. Portfolio and membership writes use row locks and expected revisions. Duplicate membership is rejected by the primary key. Audit UPDATE/DELETE is rejected by a database trigger.

The provider composes these persisted membership records with read-only project status/revision from `project_lifecycle_projects`. Project revisions and opaque source-reference revisions are independent version axes; they are never forced to be numerically equal. A required injected `PortfolioSourceReferenceReader` validates the exact tenant/project/source locator and source revision. Missing or stale references fail closed. The provider also rejects unknown/cross-tenant portfolios and stale Engineering project revisions. It derives only the membership-state counts; it does not calculate engineering KPIs.

## Acceptance criteria

- Portfolio snapshots are tenant-scoped and include a stable portfolio id.
- Membership records preserve membership state, portfolio revision, authoritative project revision and source-reference revisions.
- Duplicate projects/memberships are rejected.
- Summary counts are derived only from persisted membership status.
- Result references remain opaque links to authoritative project/domain results; no project calculations are duplicated.
- Source references are mandatory and revision-safe; their revisions are independently validated through the injected authoritative source-reference reader, not compared to project revision.
- Snapshot identity, timestamp and ordered content are deterministic for the same persisted revision set; the stable snapshot ID is revision-bound while the v1 wire schema remains unchanged.
- Read-model code remains independent from Backend P0 project-list adapters.
- The Portfolio Query application service re-authorizes every referenced project through an injected current-actor project authorizer; a missing authorizer fails closed.
- Provider unit tests, API authorization/error tests and PostgreSQL live integration pass on the exact final SHA before merge. ENT-06A production composition/browser consumer acceptance remains in #2032.

## Non-goals

- No portfolio analytics/KPI or cross-project financial calculation.
- No new P6 Scheduling, Progress/EVM, Resource/Cost or financial formulas.
- No decision mutation/approval workflow in this stage.
- No use of `PortfolioQueryAdapter.list_projects` as a membership source or fallback.
- No project data duplication: Engineering remains authoritative for project records and calculations.

## Verified implementation evidence

- `src/construction_pm/portfolio_control_persistence.py`: canonical PostgreSQL repository, optimistic revisions, append-only audit, read-only Engineering project facts adapter, injected source-reference validator contract and concrete snapshot provider.
- `tests/test_portfolio_control_persistence.py`: provider isolation, authoritative facts, stable identity/time and stale-source coverage.
- `tests/integration/test_portfolio_control_persistence_postgres_live.py`: live PostgreSQL persistence, revision, audit and source freshness coverage.
- PR #2035 merged to `main` with merge commit `bf156f686d4d8cfe4efafb088638e68841b451e9`.
- Exact tested implementation head: `3f6bdf6a6adedaac870ed397daab801d6af63d22`.
- ConstructionPM CI run `44114358321`: SUCCESS — Python 3.11, 3.12 and 3.13 full-suite jobs passed.
- PostgreSQL Integration run `44114358305`: SUCCESS — live PostgreSQL suite including this stage's integration test passed.
- Client Typecheck run `44114358228`: SUCCESS — Web, Desktop, Mobile and Client Sync jobs passed.
- The production provider is injectable through the `PortfolioQueryProvider` boundary; the application service requires per-project authorization and fails closed if it is not configured.
- Remaining integration: mount this provider in the approved ENT-06A production composition and verify the mounted dashboard consumer; tracked in #2032. This is not a reason to recreate the source store or provider.
