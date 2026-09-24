# Stage 33.4.61 — Real PostgreSQL Sync-State Integration

A live PostgreSQL CI workflow now exercises sync-state persistence and concurrent idempotency behavior.

## Scope

The test performs a real round-trip through `sync_idempotency` and runs two concurrent requests against the same tenant/project/idempotency key.

## Verification rule

The workflow itself is not evidence of a successful run. Runtime completion requires a successful GitHub Actions execution.

The race assertion intentionally checks that database uniqueness prevents two successful identities for the same idempotency key; exact driver exception details remain database/runtime-specific.
