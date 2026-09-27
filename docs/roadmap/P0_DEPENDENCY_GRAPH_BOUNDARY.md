# P0 Dependency Graph Boundary

Version: v1

This boundary persists tenant/project-scoped dependency edges with optimistic revisions, audit and idempotency.

Supported dependency types are contract labels only. This module does not calculate dates, duration, critical path, progress, EVM, resources, cost, or calendar semantics.

Repositories own persistence mechanics; the application service owns transaction/idempotency orchestration. PostgreSQL integration must reuse existing transaction/idempotency primitives.

Next integration point: PostgreSQL repository and transaction tests.
