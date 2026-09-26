# Stage 34.1 — Shared Control Intelligence

Status: **100% — contract/domain foundation hardened, merged, and runtime-verified on main (2026-09-26).**

## Implemented packages
- Cross-domain dependency graph with revision-scoped nodes, typed relationships, tenant/project scope, and source/target revision coherence.
- Auditable control-intelligence result with mandatory source references and timezone-aware timestamps.
- Revision-scoped scenario request/proposal boundary; proposals cannot mutate authoritative state.
- Cross-domain impact contract linking Schedule/Progress/EVM/Resource/Cost and other construction domains.
- Natural-language schedule query contract with revision scope and traceable answers.
- Predictive schedule-risk boundary with model version, confidence and source evidence; no risk formula is defined here.
- Change/Claim impact links to schedule/cost evidence with application approval boundary.
- Portfolio control/decision/action boundaries were subsequently hardened in Stage 34.2 and remain separate from authoritative project calculations.

## Stage 34.1 hardening completed
PR #154 was merged to main as commit 871fb296a0b81b1fddf9597e5d58a168e269e1cd.

The hardening closed the audited Issue #152 gaps:
- DependencyGraph now requires validated tenant/project/project_revision scope.
- Dependency edges must match the current revisions of their referenced source and target nodes.
- Shared control-intelligence enum boundaries reject raw string values where typed enum members are required.
- Boolean and scalar validation is enforced at contract boundaries.
- Result timestamps require timezone information with a non-null UTC offset.
- Regression tests cover the new scope, revision, enum, scalar, boolean, and timestamp boundaries.

The implementation remains outside Primavera P6 Scheduling/Calendar/Progress-EVM/Resource-Cost/financial calculation semantics.

## Contract alignment
shared/contracts/dependency-graph.v1.schema.json requires contract_version, scope tenant/project/project_revision, revision-bounded nodes and edges, and the defined dependency relation enum set. The Python boundary now enforces the corresponding scope, revision, and typed-enum invariants at runtime.

## Verification
- PR #154 head 2d26a315738137e855cbb1bbda1d5d15880c4553: ConstructionPM CI run 36280012154 passed; Client Typecheck run 36280012175 passed.
- Post-merge main commit 871fb296a0b81b1fddf9597e5d58a168e269e1cd: ConstructionPM CI run 36280198294 passed; Client Typecheck run 36280198290 passed.
- PostgreSQL Sync State Integration run 36280198317 was triggered for the same main commit and was still in progress at the time of this documentation update; therefore this document does not claim that PostgreSQL runtime verification had completed.
- The contract hardening itself introduced no database schema or persistence changes.

## Mandatory boundary
These contracts do not redefine or duplicate Primavera P6 scheduling, calendar, duration, Progress/EVM, Resource/Cost or financial formulas. Client applications must consume these versioned contracts and must not become an authoritative calculation engine.

## Next
Stage 34.1 is closed for implementation unless a new regression is discovered. The workflow proceeds to the next open platform/product gate; completed Stage 34.1 work should not be redesigned or duplicated.
