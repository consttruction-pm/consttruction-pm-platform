# Stage 33.4.2 — Shared Client Integration Contract

**Status: 100% for backend-owned contract support.**

The Resource API emits explicit `resource.v1` contract and operation identifiers on successful Resource and ResourceAssignment mutation responses. The schema is published under `docs/contracts/resource_api_v1.schema.json` for Web, Desktop and the current client foundation.

Canonical decimal serialization, ProjectContext, optimistic revisions, idempotency and stable errors remain authoritative application/API behavior.

No client UI or Scheduling/P6, Progress/EVM, Resource/Cost or calendar calculation semantics were changed.
