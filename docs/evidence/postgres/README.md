# PostgreSQL persistence evidence — R1 (2026-11-20)

Executed against a real PostgreSQL 14.24 server, not a mock and not SQLite.

| Item | Value |
| --- | --- |
| Engine | PostgreSQL 14.24 (Ubuntu 14.24-0ubuntu0.22.04.1) |
| Target | `127.0.0.1:5432/<local database>` (DSN never printed or committed) |
| Script | `scripts/verify_postgres_persistence.py` |
| Evidence | `docs/evidence/postgres/persistence.json` |
| Result | **7 / 7 checks passed** |

## Checks

| Check | Result | Meaning |
| --- | --- | --- |
| `bootstrap_is_idempotent_and_additive` | pass | second bootstrap run creates no new table and drops none |
| `session_survives_commit_in_a_new_process` | pass | login → commit → **separate process** resolves the session in tenant A |
| `tenant_isolation` | pass | tenant B sees 0 rows of tenant A's users and tasks |
| `task_row_persisted` | pass | Enterprise task JSON survived commit and is re-read from the table |
| `no_plaintext_secrets` | pass | the password is absent from `identity_users`; the raw token is absent from `identity_sessions` |
| `logout_revokes_session` | pass | revoke writes through |
| `revoked_session_unresolvable_in_new_process` | pass | after revoke, a new process resolves nothing |

## Schema bootstrap on an empty database

```
before 0
after run 1: 27 tables
after run 2: 27 tables
```

The production bootstrap (`initialize_production_schema`) creates exactly **27 tables**. The other
156 tables found by scanning repository DDL (183 total) are created lazily by their own
repository `initialize()` when first used — that is the existing pattern and is not changed here.

## Repository integration suite on the live server

```
CONSTRUCTION_PM_POSTGRES_DSN=... python3 -m pytest tests/integration -q
458 passed in 4.51s
```

These are the repository's own live tests (baseline, cost, expenses, field registry, schedule
input snapshot, document search, concurrency), all skipped in CI without a DSN and all green here.

## Legacy storage decision

- Production forbids SQLite: `production_readiness.py` raises `SQLITE_FORBIDDEN_IN_PRODUCTION` and
  `ProductionSettings` rejects any non-`postgres://` DSN.
- `src/construction_pm/preview/storage.py` uses SQLite **only** for the Vercel preview adapter; it
  is not reachable from the production entrypoint, so there is no data to migrate from it.
- The knowledge corpus has both stores (`knowledge/sqlite_store.py`, `knowledge/postgres_store.py`)
  sharing one `SCHEMA_VERSION`; `PostgresKnowledgeStore` subclasses the SQLite store, so the
  mapping is the same schema, not a parallel model.
- No production table was created, dropped or altered in this increment. No second database was
  introduced. No destructive migration was executed.

## Reproduce

```bash
export CONSTRUCTION_PM_POSTGRES_DSN=postgresql://...
python3 scripts/verify_postgres_persistence.py --out docs/evidence/postgres/persistence.json
python3 -m pytest tests/integration -q
```

Remaining external dependency: the deployed runtime still needs the owner-provided production DSN
(`CONSTRUCTION_PM_DATABASE_URL`) in Vercel. Verification here proves the code path; it does not
claim the production instance was touched.
