# Infrastructure

Deployment, database, containers, configuration and environment-specific adapters belong here.

Infrastructure must not leak into the Shared Domain/Calculation Core.

# Production composition seam

The repository intentionally keeps the outer process/server ownership outside the domain and transport modules.
The explicit application composition entry point is:

`construction_pm.http.production_composition.build_project_lifecycle_wsgi_app`

A deployment/runtime owner supplies the authenticated `ProjectLifecycleAPI`, persisted schedule snapshot and `CalculationContext` repositories, calendar registry factory, and authorization policy.
The composition seam wires the authoritative `ScheduleQueryAPI` into `ProjectLifecycleHttpRoutes` and the dependency-free WSGI transport.

This is the supported seam for POST `/api/v1/schedule/query`. It must not be replaced by a second scheduler/evaluator or client-side calculation logic.

## Persisted resource-leveling composition

For date-based schedules that request resource leveling, the production composition must receive the same runtime's authorized `P6ResourceReadAPI` and exact-version calendar repositories. Supply these together to `build_project_lifecycle_wsgi_app`:

- `resource_read_api`
- `resource_calendar_master_repository`
- `resource_calendar_snapshot_repository`
- `resource_calendar_exception_repository`
- `resource_calendar_work_hours_repository`

The composition builds `build_persisted_resource_leveling_input_resolver` automatically when all five are present. Partial configuration is rejected. A custom `leveling_input_resolver` may be supplied instead, but it cannot be combined with the repository arguments. Missing resolver configuration does not silently disable leveling; a leveling-enabled query fails closed.

The resolver reads the exact snapshot's tenant/project/revision through the authenticated resource read API, captures assignment and time-phased demand records, derives seed dates/floats through the Shared Scheduling Core, resolves each resource calendar by the exact ID+version including stored exceptions/work-hour rules, and returns a frozen input with snapshot, calculation, raw-facts, and calendar-manifest hashes. Those identities are included in the calculation run identity. Do not provide a permissive calendar-by-ID fallback.

## Durable AI learning-memory PostgreSQL runtime

The learning-memory repository has SQLite and PostgreSQL adapters. Production must inject a durable PostgreSQL adapter into the existing composition seam; do not use the Preview SQLite database for customer knowledge.

Use `construction_pm.ai_learning_memory_runtime.PostgresAILearningMemoryRuntime` as the application-lifetime owner:

```python
from construction_pm.ai_learning_memory_runtime import (
    PostgresAILearningMemoryRuntime,
)
from construction_pm.http.production_composition import (
    build_project_lifecycle_wsgi_app,
)

memory_runtime = PostgresAILearningMemoryRuntime.open_from_environment()
if memory_runtime is None:
    raise RuntimeError("AI_LEARNING_MEMORY_DATABASE_NOT_CONFIGURED")

try:
    app = build_project_lifecycle_wsgi_app(
        # existing authenticated lifecycle, schedule and policy dependencies
        ai_learning_memory_repository=memory_runtime.repository,
        # ...
    )
    # Serve the app with the existing production server.
finally:
    memory_runtime.close()
```

Server-only configuration:
- `CUBI_AI_LEARNING_MEMORY_DB_BACKEND=postgresql`
- `CUBI_AI_LEARNING_MEMORY_DATABASE_URL=postgresql://...` (application role)
- `CUBI_AI_LEARNING_MEMORY_MIGRATION_DATABASE_URL=postgresql://...` (migration role; required remotely)
- Remote PostgreSQL URLs must carry `sslmode=require`, `verify-ca` or `verify-full`.
- `CUBI_AI_LEARNING_MEMORY_CONNECT_TIMEOUT_SECONDS` is optional (1–30; default 10).

For remote databases, both DSNs must target the same host/port/database and the same `options=-csearch_path=cubi_ai_memory`, but use different PostgreSQL usernames. Create the non-public `cubi_ai_memory` schema owned by the migration role before startup. The migration role creates tables/indexes/triggers in that schema. Grant the application role schema USAGE and SELECT/INSERT on the two data tables; revoke UPDATE/DELETE. Runtime startup verifies these grants and refuses a remote runtime role with broader mutation rights. Local loopback integration tests may use one DSN for both roles.

When unset/disabled, the factory returns `None`; it never silently falls back to SQLite. Do not log either DSN. The runtime applies checked migrations using the migration connection, then opens a separate least-privilege application connection and leaves it idle after its startup checks. The deployment must close the runtime on graceful shutdown.

This repository configuration does not provision PostgreSQL or set provider backups. Production still requires a durable managed database, separate secret credentials, encrypted automated backups, restore drills, monitoring and an explicit policy mapping for learning-memory grants.


## Encrypted learning-memory backup and restore

The repository now includes an operational logical-backup tool at
`python -m construction_pm.ai_learning_memory_backup`. It is deliberately
separate from the Preview SQLite reset backup.

### Backup contents and consistency

The backup is a PostgreSQL custom-format archive encrypted directly to an
`age` recipient. A plaintext SQL/custom dump is never written to disk. The
exported repeatable-read snapshot is held open while `pg_dump` reads it, so the
three learning-memory tables are taken from one consistent database snapshot:

- `ai_learning_memory_records`
- `ai_learning_memory_audit_events`
- `ai_learning_memory_schema_migrations`
- the `cubi_reject_ai_learning_mutation` trigger function and table triggers

The tool requires a dedicated, non-public PostgreSQL schema and refuses it
unless it contains exactly the three memory tables and the single append-only
trigger function; indexes and triggers are included as schema dependencies.
It also refuses migration versions other than 3 or missing append-only guards.
The output is a mode-0600 encrypted archive plus a checksum manifest and an
Ed25519 signature over that manifest, inside a mode-0700 destination directory.
The signature binds the archive hash, schema name, migration version and
source-database fingerprint. Thus an archive encrypted by an arbitrary party
with the public age recipient still cannot be accepted without the trusted
signing key. Connection credentials are passed to libpq through the child
process environment, not command-line arguments, and tool failures never print
the DSN or raw subprocess output.

Create the schema owned by the migration role, then grant the runtime and
backup roles only the rights they need. The backup DB account should be a
dedicated read-only role with CONNECT, schema USAGE and SELECT on the three
memory tables. The restore account needs CREATE on a new empty target database;
the dump recreates the isolated memory schema. Remote URLs should use
`sslmode=verify-full` and the provider CA certificate where available. Use a
dedicated persistent, access-controlled mount for the destination; an
ephemeral application filesystem or the Preview `.preview` directory is not
a backup target.

### Server configuration

Install `pg_dump` and `pg_restore` from the same PostgreSQL major version as
the source database (and use a compatible client when restoring), plus `age`
and OpenSSL. Install the CUBI package in the deployment virtual environment;
create a dedicated `cubi-backup` OS account; and mount durable backup storage at
`/mnt/cubi-encrypted-backups`. Store the following in
`/etc/cubi/learning-memory-backup.env` (owner-readable only, mode 0600):

```sh
CUBI_AI_LEARNING_MEMORY_BACKUP_DATABASE_URL=postgresql://backup_role:REDACTED@db.example/production?sslmode=verify-full&sslrootcert=/etc/cubi/db-ca.pem&options=-csearch_path=cubi_ai_memory
CUBI_AI_LEARNING_MEMORY_BACKUP_AGE_RECIPIENT=age1REPLACE_WITH_PUBLIC_RECIPIENT
CUBI_AI_LEARNING_MEMORY_BACKUP_DIR=/mnt/cubi-encrypted-backups
CUBI_AI_LEARNING_MEMORY_BACKUP_SCHEMA=cubi_ai_memory
CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_PRIVATE_KEY_FILE=/etc/cubi/learning-memory-signing-key.pem
```

The DSN and public recipient above are placeholders, not live credentials.
Generate an Ed25519 signing keypair on the protected backup host (or deliver it
from a managed secret store); keep the private key readable only by
`cubi-backup`, and distribute the public key to restore/verification operators:

```sh
openssl genpkey -algorithm ED25519 -out /etc/cubi/learning-memory-signing-key.pem
chmod 0600 /etc/cubi/learning-memory-signing-key.pem
openssl pkey -in /etc/cubi/learning-memory-signing-key.pem -pubout -out /etc/cubi/learning-memory-signing-key.pub.pem
```

Never store a database password, age private identity or signing private key in
Git. The backup service needs the public age recipient and signing private key;
authorized verification/restore operators need the age identity and signing
public key. The optional
`CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_KEY_PASSPHRASE` environment variable
unlocks a passphrase-protected PEM signing key. Supply it from the host's secret
manager, not a checked-in file.

### Commands

Create a backup:

```sh
python -m construction_pm.ai_learning_memory_backup backup
```

Verify the encrypted archive checksum, decryptability and PostgreSQL archive
catalogue (set the private identity file outside the repository first):

```sh
export CUBI_AI_LEARNING_MEMORY_BACKUP_AGE_IDENTITY_FILE=/secure/path/age-identity.txt
export CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_PUBLIC_KEY_FILE=/secure/path/learning-memory-signing-key.pub.pem
python -m construction_pm.ai_learning_memory_backup verify /mnt/cubi-encrypted-backups/FILE.dump.age
```

Restore is intentionally non-destructive. It requires a different, pristine
target database (only the standard catalogs and empty `public` schema may
exist), a valid age identity, the trusted signing public key, and the exact
explicit confirmation value. It refuses a source-equal target, an existing
memory schema, or any unrelated user object. The archive recreates its
dedicated schema. Restore runs in one PostgreSQL transaction and then verifies
migration level 3, the three tables, the trigger function and both append-only
triggers.

```sh
export CUBI_AI_LEARNING_MEMORY_BACKUP_SIGNING_PUBLIC_KEY_FILE=/secure/path/learning-memory-signing-key.pub.pem
export CUBI_AI_LEARNING_MEMORY_RESTORE_DATABASE_URL='postgresql://restore_role:REDACTED@db.example/restore_drill?sslmode=verify-full&sslrootcert=/etc/cubi/db-ca.pem'
export CUBI_AI_LEARNING_MEMORY_RESTORE_CONFIRM=RESTORE_TO_EMPTY_DATABASE
python -m construction_pm.ai_learning_memory_backup restore /mnt/cubi-encrypted-backups/FILE.dump.age
```

Run restore drills against a disposable database, never against the live
application database. After restore, grant the application role only the
required schema USAGE and table SELECT/INSERT privileges; do not grant
UPDATE/DELETE. The restore role needs CREATE on the target database (the archive creates the
dedicated schema).

### Daily schedule template and limits

Hardened systemd templates are provided at:

- `infra/systemd/cubi-learning-memory-backup.service`
- `infra/systemd/cubi-learning-memory-backup.timer`

They run a daily encrypted and signed logical backup at 02:15 UTC with a
randomized delay. Before enabling them, create the OS account, install the
service environment file (including the signing private-key path), provision
and mount the durable destination, and confirm that the backup role can read
all three tables. The template is for a self-hosted
systemd host; managed hosting platforms must use their own supported scheduler
and persistent object/storage service.

This tool provides **full logical snapshots of the learning-memory data**, not
incremental/WAL backups. Configure provider-managed point-in-time recovery or
WAL archiving separately for the required recovery-point objective. Retention,
off-host replication, object-lock policy, alerting, backup-key rotation and
automated restore drills still need explicit deployment policy and operational
configuration. The repository templates do not provision storage, schedule a
live service, or prove a production restore. Do not mark production backup
acceptance complete until a real encrypted backup has been stored off-host and
a restore drill has passed against a separate database.
