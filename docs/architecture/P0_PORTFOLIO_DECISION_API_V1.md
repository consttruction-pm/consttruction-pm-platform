# Portfolio Decision API v1

## Purpose
Expose the existing Portfolio Decision application and persistence boundary through a versioned transport adapter.

## Contract
- Version: `portfolio-decision.v1`
- Create requires tenant-scoped authorization, Portfolio Admin permission, actor identity, idempotency key, and timezone-aware audit timestamp.
- Read requires tenant-scoped `PROJECT_READ` authorization.
- Responses preserve the existing `PortfolioDecisionBoundary` payload and add the contract version and persistence revision.

## Ownership
Domain lifecycle semantics remain in Control Intelligence. Persistence owns revision, idempotency, and audit atomicity. This adapter adds no scheduling, EVM, resource, cost, or financial calculations.

## Verification
Focused tests cover version validation, tenant isolation, response versioning/revision, and actor identity enforcement.
