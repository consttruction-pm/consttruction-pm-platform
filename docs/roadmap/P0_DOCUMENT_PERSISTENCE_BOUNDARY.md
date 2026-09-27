# P0 Document Persistence Boundary

## Scope

This package establishes the backend persistence boundary for project documents without implementing OCR/search engines or storing document bytes inside PostgreSQL.

Supported resource types:
- contract
- drawing
- correspondence
- rfi
- submittal
- delay_claim
- evidence

## Boundary rules

- Tenant and project context are mandatory.
- Document bytes remain behind an opaque `storage_ref`.
- Content integrity is represented by a SHA-256 content hash.
- Creates are idempotent within tenant/project scope.
- Updates require an explicit expected revision.
- Revisions are bounded by the existing JavaScript-safe integer ceiling.
- Audit history is append-only.
- Linked activity/cost/progress references are opaque IDs; no scheduling, cost, progress or financial formulas are introduced.
- OCR, search indexing, approval policy and storage-provider implementation remain separate adapters/lifecycle stages.

## Acceptance

- Versioned P0 document resource contract exists.
- PostgreSQL persistence supports create/read/update and append-only audit.
- Same-key identical create replays without a second audit event.
- Same-key different payload is rejected.
- Stale revisions are rejected.
- Revision overflow at the safe ceiling is rejected.
- Invalid document type/hash/context metadata is rejected.

## Next boundary

The next document work may add approval lifecycle and provider-backed OCR/search adapters without moving business calculations into the repository.
