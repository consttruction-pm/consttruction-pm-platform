# P6 Document Retention and Disposition Contract

Status: implemented on `agent3/document-retention-2026-11` (Issue #1799 Workstream 4). Retention planning and deliberate content disposition are implemented; no timer, scheduler or legal-discovery workflow is claimed.

## Model

Retention is decided per document metadata record. Two additive tables are created with `CREATE TABLE IF NOT EXISTS`; existing databases are not rebuilt.

| Table | Key | Purpose |
| --- | --- | --- |
| `project_document_retention` | `(tenant_id, project_id, document_id)` | policy, hold flag, optimistic `revision` |
| `project_document_disposition` | `(tenant_id, project_id, document_id, version)` | append-only evidence of deleted bytes |

A policy carries `retain_days` (`0..36500`), `legal_hold`, a non-empty reason, the updating actor and an optimistic `revision`. Content versions are immutable; retention never rewrites a version row.

## Policy updates

`set_policy` requires project-write and an actor equal to the session user. Creation expects `expected_revision=0`; updates must match the current revision and increment it. A stale revision returns `409 DOCUMENT_RETENTION_REVISION_CONFLICT`, and a lost create race also returns that conflict instead of overwriting. Each successful update appends a `retention_updated` audit event to the document history without changing metadata fields.

## Eligibility

Eligibility is computed for every content version and never inferred from a flag. Values are:

| Reason | Meaning |
| --- | --- |
| `no_policy` | no retention policy exists |
| `legal_hold` | policy sets a legal hold |
| `not_yet_due` | `now < uploaded_at + retain_days` |
| `disposed` | a disposition row already exists |
| `eligible` | policy exists, hold is clear and the window has elapsed |

`expires_at` is always `uploaded_at + retain_days`; with `retain_days=0` the version is eligible immediately after upload. `read` and `plan` are read-only and require project-read.

## Disposition

`dispose` is deliberately separate from policy and is never automatic. It requires project-write and:

1. `confirm` exactly equals `"{document_id}:{version}"`;
2. a policy exists;
3. `legal_hold` is false;
4. the content version exists;
5. no disposition exists for that version;
6. `occurred_at >= uploaded_at + retain_days`.

The object bytes are deleted through the configured storage adapter first (a missing object is tolerated so a retry can finish), then an append-only disposition row records `content_hash`, reason, actor and time. Metadata, document history and the content version row remain so the deletion is auditable. A second attempt returns `409 DOCUMENT_CONTENT_ALREADY_DISPOSED`.

Once a disposition exists, `DocumentApplicationService.download_content` refuses the version with `409 DOCUMENT_CONTENT_DISPOSED`, regardless of scan status. Legacy metadata-only references have no version and therefore no disposition; they are unaffected apart from existing quarantine rules.

## HTTP

| Method and path | Meaning |
| --- | --- |
| `GET /api/projects/{p}/documents/{id}/retention` | policy, dispositions and eligibility, `200` |
| `PUT /api/projects/{p}/documents/{id}/retention` | create/update policy with `expected_revision`, `200` |
| `POST /api/projects/{p}/documents/{id}/content/{version}/dispose` | delete bytes and record disposition, `200` |

Missing document/version/policy → `404`; revision conflict, legal hold, immature window, already disposed and disposed download → `409`; bad confirmation and invalid fields → `400`; missing retention service → `503 DOCUMENT_RETENTION_UNAVAILABLE`; authorization failures → `403`.

## Storage and parity

`SQLiteDocumentRetentionStore` and `PostgresDocumentRetentionStore` share the same SQL and row serialization, differing only in the placeholder. Both use `ON CONFLICT DO NOTHING` for the create race and `revision` in the `UPDATE ... WHERE` clause for optimistic concurrency. `dispose` uses the same `DocumentBinaryStorage.delete` port as the local and S3-compatible adapters, so byte removal works for either backend.

## Out of scope

- No scheduler executes disposition; an authorized caller must invoke it. A deployment may call `plan` for reporting.
- Legal hold is a boolean on the policy, not a matter/litigation workflow.
- OCR text, derived previews, backups and object-store lifecycle rules are not purged by this slice.
- UI affordances, notifications and deployment configuration are external.
