# Stage 33.4 — Offline Mutation Queue Context Hardening

Date: 2026-09-24

## Purpose
Harden the backend-owned offline mutation queue so removal is explicitly project-context scoped and SQLite adapters participate in an existing transaction boundary.

## Rules
- Queue identity includes tenant/company/project/operation/idempotency key.
- Removal must carry the full queued mutation context; a key from one project must not remove another project's item.
- SQLite queue writes do not commit when an outer transaction already owns the connection.
- Queue persistence does not execute business calculations.
- The portable queue contract remains independent of SQLite.

## Verification
- Cross-context removal regression for in-memory and SQLite adapters.
- Existing-transaction rollback regression.
