# Stage 33.4.2 — Shared Client Integration Contract

**Status: 100% for backend-owned contract support.**

The Resource API now emits the explicit `resource.v1` contract version and operation identifier on successful Resource and ResourceAssignment mutation responses. The schema is published under `docs/contracts/resource_api_v1.schema.json` for Web and Desktop consumers.

Canonical decimal serialization remains unchanged. Revision, idempotency, ProjectContext and stable error behavior remain application-owned semantics.

This backend substage does not implement client UI and does not redefine Scheduling/P6, Progress/EVM, Resource/Cost or calendar calculations.

Next backend-owned support: contract/error parity regression for Web and Desktop integration.
