# P6 Database Migration and Repository Parity Contract

Status: implemented on `agent3/database-parity-2026-11` (Issue #1799 Workstream 5). This covers the document, OCR, retention and exchange stores changed by Workstreams 2 and 4. It does not claim that every SQLite-only store has a PostgreSQL twin.

## Audited tables

| Table | Owner | SQLite | PostgreSQL |
| --- | --- | --- | --- |
| `project_documents` | document metadata | yes | yes |
| `project_document_audit` | document history | yes | yes |
| `project_document_content` | immutable content versions | yes | yes |
| `project_document_ocr` | durable OCR queue | yes | yes |
| `project_document_retention` | retention policy | yes | yes |
| `project_document_disposition` | append-only disposition | yes | yes |
| `project_exchange_import_run` | exchange run log | yes | yes |
| `project_exchange_idempotency` | apply idempotency | yes | yes |

A live parity test introspects both catalogues and asserts equal column sets, nullability, primary-key column order, unique constraints and explicit index column sets for these tables.

## Type and serialization strategy

- Timestamps: SQLite stores ISO-8601 text; PostgreSQL stores `timestamptz` where the table is relational and ISO text inside JSON snapshots. Parsing normalizes to UTC, and a live test asserts microsecond fidelity.
- JSON: SQLite stores text; PostgreSQL uses `jsonb` for content versions. The shared `_to_json`/`_from_json` serializer parses either driver representation, so no dialect branch exists in domain code.
- Identifiers and hashes stay `TEXT`; counters and versions use `INTEGER` on SQLite and `BIGINT`/`INTEGER` on PostgreSQL. No audited table holds a `Decimal` column; Decimal behavior is covered by the existing P6/tracking and expense suites.

## Additive migration rules

`initialize()` only runs `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS` and, where a store predates a column, an additive `ALTER TABLE ... ADD COLUMN` with a non-destructive default. There is no `DROP`, no table rebuild and no data rewrite. Running `initialize()` on an existing database preserves rows and unknown columns.

The exchange run log now declares `idx_exchange_run_scope (tenant_id, project_id, dataset, run_id)` in both dialects. SQLite previously omitted it; existing databases receive it on the next `initialize()`.

Content version inserts use `INSERT ... ON CONFLICT DO NOTHING` and then resolve the conflict through the idempotency index. A same-key concurrent replay returns the stored row; a different key racing for the same version fails closed with `DOCUMENT_CONTENT_VERSION_CONFLICT` and writes no partial row. This replaces driver-specific uniqueness exceptions as the normal race outcome.

## Fresh-install and upgrade coverage

- SQLite `tests/test_database_migration_parity.py`: fresh install of all audited stores, double `initialize()`, row preservation, a pre-scan `project_document_content` JSON row upgraded to `unscanned` defaults, creation of the new OCR/retention tables, and index creation after a simulated legacy database.
- Live PostgreSQL `tests/integration/test_database_parity_postgres_live.py`: the same upgrade path in a disposable schema, double `initialize()`, preserved legacy exchange runs and content JSON, plus the parity catalog comparison.
- Existing store-specific tests cover the report parameter and report-schedule column additions on SQLite.
- Live PostgreSQL `tests/integration/test_report_postgres_live.py` covers the PostgreSQL report definition/run and schedule stores: idempotency, revisions, append-only audit, immutable runs, CRUD, two-thread claim exclusivity, lease reclaim, failure backoff, rollback and an explicit SQLite/PostgreSQL output parity check.

## Concurrency invariants

- Document metadata updates keep an explicit revision guard (`expected_revision`) and return `DOCUMENT_REVISION_CONFLICT`; a lost update never overwrites the newer row.
- Retention policy updates use `revision` in the `UPDATE ... WHERE` clause and the same optimistic conflict code.
- Exchange apply idempotency and sync-state idempotency rely on primary-key uniqueness; the live sync conflict suite proves one delegate execution across connections.
- The new live tests race two content appends for the same version: one row results, same-key callers receive identical versions, different-key callers receive one success and one bounded persistence error.

## Repeatable live tests

The live suites use per-run UUIDs and disposable schemas, so they can run repeatedly against the same database. The Workstream 5 acceptance run is:

```bash
export CONSTRUCTION_PM_POSTGRES_DSN="postgresql://postgres:@/postgres?host=/tmp/pgdata"
python -m pytest tests/integration -q   # first run
python -m pytest tests/integration -q   # second run, same database
```

`tests/integration/test_postgres_atomic_conflict_live.py` already generates a per-process `RUN_ID`, so fixed-key collisions between runs are gone.

## Report store parity

`PostgresReportStore` and `PostgresReportScheduleStore` are behavioral twins of the SQLite stores. They use `%s` placeholders, `TEXT` timestamps and JSON columns, never commit implicitly, and create their schema additively with `CREATE TABLE/INDEX IF NOT EXISTS` plus `information_schema`-guarded `ADD COLUMN` upgrades. Definition and schedule writes use conditional `UPDATE`/`DELETE ... WHERE revision = expected` so a competing writer receives the same revision-conflict code instead of a lost update. Lease claims use a conditional `UPDATE` on `claim_token`/`claimed_until`; `complete`/`fail` verify the token, and `commit_claim()` makes the lease durable before execution.

The preview runtime (`preview/runtime.py`) still composes SQLite stores for its in-process demo. A production PostgreSQL runtime must select the PostgreSQL twins explicitly; this contract does not claim that composition is wired.
