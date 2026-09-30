# P0 Dependency Graph Boundary

Version: v1

This boundary persists tenant/project-scoped dependency edges with optimistic revisions, audit and idempotency.

Supported dependency types are contract labels only. This module does not calculate dates, duration, critical path, progress, EVM, resources, cost, or calendar semantics.

Repositories own persistence mechanics; the application service owns transaction/idempotency orchestration. PostgreSQL integration must reuse existing transaction/idempotency primitives.

PostgreSQL repository and transaction integration is implemented on current main; remaining work is focused on runtime verification and regression maintenance.


## Shared Core conformance
The persistence adapter projects explicitly typed dependency domains/relations through `dependency_graph_conformance.py`. Unknown domain/relation values are rejected rather than inferred. The projection preserves tenant/project scope, project graph revision, and independent source/target node revisions.

Conformance coverage includes schedule→progress→EVM, resource/cost→schedule, change/claim links, invalid domain/relation rejection, revision mismatch rejection, and deterministic projection.

Authoritative scheduling, progress/EVM, resource/cost and financial semantics remain in Shared Core.
