# CUBI AI Learning Memory — Storage, Versioning and Authorization Contract

**Status:** Phase A implementation contract  
**Current record payload schema:** `1.0`  
**Current database migration level:** `3`  
**Backends:** SQLite and PostgreSQL

This document separates three versions that serve different purposes. They must not be conflated or advanced together.

## 1. Three independent version concepts

| Version | Meaning | Current value | Change rule |
|---|---|---:|---|
| `schema_version` | Shape and semantics of one serialized learning record | `1.0` | Keep the v1.0 decoder immutable. A future payload-shape change needs a new explicitly supported payload version and a tested decoder/normalization path. |
| `record_version` | Immutable revision of one logical lesson/knowledge record | Starts at `1` | Append consecutive versions; never update an existing revision. The record's privacy scope and ownership identity are immutable across revisions. |
| `ai_learning_memory_schema_migrations.version` | Physical database table/index/trigger layout | `3` | Append new migration numbers. Never rewrite a released migration name or checksum. |

A fixed record payload schema of `1.0` does **not** freeze the database at version 1. Database evolution is tracked independently in the migration-history table.

When the record payload contract needs to evolve, add an explicit supported payload version to the domain contract and codec. Do not silently reinterpret a v1.0 payload and do not rewrite append-only historical records in place.

## 2. Database migrations

The migration table records `version`, `migration_name`, SHA-256 `checksum` and UTC `applied_at`. Startup validates the migration history and the required table columns and primary keys. Unknown versions, newer databases, checksum drift, incomplete legacy schemas and incompatible primary keys fail closed.

| Version | Migration | Effect |
|---:|---|---|
| 1 | `create_ai_learning_memory_records` | Creates the append-only record table and scope index. A pre-existing PR #1542 v1 table is adopted only when its full column set and composite primary key match; stored rows are not rewritten. |
| 2 | `create_ai_learning_memory_audit_events` | Creates metadata-only audit events and a tenant/project/time index. |
| 3 | `enforce_append_only_learning_memory_and_audit_rows` | Adds database-level UPDATE/DELETE guards to both records and audit events. SQLite uses triggers; PostgreSQL uses a PL/pgSQL trigger function and row triggers. |

### Rules for every future migration

1. Add a new migration tuple with the next integer version, a unique stable name and a checksum over the exact DDL/guard definitions.
2. Never edit the DDL or checksum for migration 1, 2 or 3 after release. A correction is a new migration.
3. Implement and test the migration on both SQLite and PostgreSQL.
4. Test a clean database, an existing v1 legacy database, repeated initialization, incompatible schema rejection, checksum mismatch, future-version rejection and caller-owned transaction behavior.
5. Preserve rows and previous record payloads. Do not use `CREATE TABLE IF NOT EXISTS` as a substitute for validating an existing schema.

### Transaction ownership

Repository operations use caller-aware transaction scopes:

- SQLite starts an immediate transaction when the repository owns the operation; otherwise it uses a savepoint and never commits the caller's transaction.
- PostgreSQL starts and commits a transaction only when the connection is idle; an existing caller transaction is protected by a savepoint and remains caller-owned.
- Learning record creation and its success audit event are one atomic repository operation.
- Application reads and their audit events share one transaction.

## 3. Append-only record and audit rules

- The primary key for a knowledge record is `(record_id, record_version)`.
- The first revision is version 1. Each later revision must be exactly the previous revision plus one.
- `scope`, `owner_user_id`, `tenant_id` and `project_id` cannot change between versions of one record.
- Updating or deleting persisted record rows is blocked by database triggers.
- Audit events are append-only and contain metadata only: actor, tenant/project, operation, outcome, record reference, reason code, result count and UTC timestamp. They do not copy lesson text or conversation transcripts.
- A newer candidate, rejected or retired revision suppresses older versions from current retrieval. Exact-version reads remain available only when that exact record is visible to the trusted caller scope.

Physical deletion, retention windows and user-requested erasure are not implemented in Phase A. They require a separately reviewed retention/tombstone and backup-expiry design; direct SQL UPDATE/DELETE is intentionally blocked.

## 4. Privacy scopes and permissions

All retrieval flags default to deny. A caller cannot authorize itself by supplying a scope object or by putting an owner ID in an HTTP body.

The application service derives the retrieval scope from the authenticated server-side `AuthorizationContext` and the current authorization policy. Dedicated permission grants are required for:

- User-private read/write.
- Project-private read/write.
- Tenant-shared read/write.
- General-candidate creation and a separate candidate-review retrieval grant.
- General published read.
- General validation, publication and retirement.

These learning grants are not silently inherited from the default viewer, planner or project-admin roles. Deployments must explicitly configure them. The preview runtime uses a separate preview-only policy to grant its demo project administrator the candidate/retrieval permissions; it does not modify the default product policy.

Project-private retrieval is constrained by the exact authenticated tenant and project. The record creator is provenance; authorized members of the same project can read it. Tenant-shared retrieval needs an explicit tenant grant and a validated/published state. General candidates are never retrievable as general knowledge. General-candidate creation requires explicit consent for generalization.

The generic capture endpoint accepts only captured/candidate records. It cannot create validated or published knowledge. A holder of the explicit general-validation grant can retrieve de-identified general candidates for review, but that grant does not make candidates visible to ordinary assistant retrieval and does not grant publication. A separate reviewed administration workflow must perform validation, approval and publication.

## 5. HTTP and deployment wiring

When an `AILearningMemoryRepository` is supplied to `build_project_lifecycle_wsgi_app`, the production composition applies migrations and exposes the following session-bound project routes:

- `GET /api/projects/{project_id}/ai/learning-memory`
- `GET /api/projects/{project_id}/ai/learning-memory/{record_id}/{version}`
- `POST /api/projects/{project_id}/ai/learning-memory`

The routes require the existing opaque `cp_session` cookie. The current user, tenant, project and roles come from the authenticated project lifecycle/session services, not from request-body identity fields. There are no edit/delete or publish endpoints in this Phase A slice.

The preview runtime passes its existing SQLite connection through the real composition path. Production deployments can use `PostgresAILearningMemoryRuntime` from `construction_pm.ai_learning_memory_runtime` to establish a dedicated PostgreSQL connection, apply checked migrations, verify that the target database is writable, and inject `runtime.repository` into `build_project_lifecycle_wsgi_app`. Keep the runtime alive for the application lifetime and close it during graceful shutdown.

The connection is opt-in and default-disabled. Set `CUBI_AI_LEARNING_MEMORY_DB_BACKEND=postgresql`, the server-only `CUBI_AI_LEARNING_MEMORY_DATABASE_URL` for application reads/inserts, and `CUBI_AI_LEARNING_MEMORY_MIGRATION_DATABASE_URL` for schema migrations. Remote runtime and migration DSNs must use TLS (`sslmode=require`, `verify-ca` or `verify-full`), target the same database and use different database usernames. A remote deployment without separate migration credentials fails closed. The runtime checks that the application role has SELECT/INSERT only on the two memory tables and does not have UPDATE/DELETE. It does not print DSNs in representations or public errors. When the backend setting is unset/disabled, no database is opened and there is no SQLite or provider fallback. The outer deployment must inject a current-grant `AuthorizationPolicy`; the default role policy does not implicitly grant memory access.

For local loopback integration tests, one DSN may serve both roles. For production, keep the migration credential in a secret available only to the controlled startup/migration process; grant the application role schema usage plus SELECT/INSERT on the two memory tables and revoke UPDATE/DELETE. The repository and runtime factory establish a tested deployment seam, not a provisioned hosted database. A production operator must still supply the durable PostgreSQL service, encrypted automated backups, restore drills, monitoring and rotation of both credentials. The demo Preview service remains SQLite-backed and is not a production persistence target.

## 6. Non-goals of Phase A

Phase A does not ingest full source documents and does not grant rights to store source text. Registry presence is not a license. Each source in the 17-item register needs a separate rights/permission decision before full-text ingestion.

PDF/HTML extraction, knowledge-card production, deterministic search, admin review/publication UI, assistant/Smart Guide integration, backup/restore, retention and erasure remain later phases. No external AI/model/API, vector embeddings, generative summarization, AI OCR or cloud speech is introduced.
