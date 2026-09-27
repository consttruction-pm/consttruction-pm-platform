# P0 Dependency Graph Boundary

Version: v1

This boundary persists tenant/project-scoped dependency edges with optimistic revisions, audit and idempotency.

Supported dependency types are contract labels only. This module does not calculate dates, duration, critical path, progress, EVM, resources, cost, or calendar semantics.

Repositories own persistence mechanics; the application service owns transaction/idempotency orchestration. The PostgreSQL adapter executes each mutation inside one caller-provided transaction and locks the tenant/project graph revision row with `FOR UPDATE`.

## PostgreSQL persistence contract

A dependency mutation:

1. enters the repository transaction boundary;
2. locks the tenant/project graph revision;
3. checks idempotency and returns the prior resource for an exact replay;
4. rejects key reuse with a different fingerprint;
5. rejects a stale graph revision;
6. increments the graph revision;
7. persists the link and audit event atomically.

A failure after revision advancement rolls the revision and resource/audit writes back together.

## Shared Core conformance

The persistence adapter projects explicitly typed dependency domains/relations through `dependency_graph_conformance.py`. Unknown domain/relation values are rejected rather than inferred. The projection preserves tenant/project scope, project graph revision, and independent source/target node revisions.

Conformance coverage includes schedule→progress→EVM, resource/cost→schedule, change/claim links, invalid domain/relation rejection, revision mismatch rejection, and deterministic projection.

Authoritative scheduling, progress/EVM, resource/cost and financial semantics remain in Shared Core.

## Verification

Regression coverage includes transactional persist/replay, stale revision rejection, idempotency-key reuse, tenant/project isolation, audit history, canonical fingerprints, validation-before-mutation and atomic rollback.
