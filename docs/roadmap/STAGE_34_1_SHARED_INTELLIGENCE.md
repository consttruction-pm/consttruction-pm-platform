# Stage 34.1 — Shared Control Intelligence

Status: **initial contract package implemented — runtime verification pending**

## Package 34.1.1 — Cross-Domain Dependency Graph
- Versioned `dependency-graph.v1` contract.
- Shared domain graph nodes are tenant/project/revision scoped.
- Supported domains include Schedule, Progress, EVM, Resource, Cost, Document, Change, Claim, Procurement and Field.
- Edges describe cross-domain dependency/impact/evidence relationships without duplicating domain calculations.
- Graph rejects duplicate nodes, unknown endpoints and self-dependencies.

## Package 34.1.2 — Auditable Control-Intelligence Result
- Versioned `control-intelligence-result.v1` contract.
- Result scope carries tenant/project/authoritative project revision.
- Findings and proposed actions carry source references.
- Results require traceable source references and timezone-aware generation timestamps.

## Package 34.1.3 — Scenario Contract Boundary
- Versioned `control-scenario.v1` request contract.
- Scenario changes are explicitly proposed and revision-scoped.
- Scenario proposals are non-authoritative and cannot directly mutate project state.
- Future approval and application execution belong to the Application/API boundary.

## Boundary
This package defines contracts and domain validation only. It does not redefine or duplicate Primavera P6 scheduling, calendar, duration, Progress/EVM, Resource/Cost or financial formulas.

## Verification
Focused contract/domain tests are added. GitHub Actions runtime verification remains a separate infrastructure-dependent gate while Hosted Runner jobs fail before executable steps.
