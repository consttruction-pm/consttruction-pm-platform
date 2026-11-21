# CUBI canonical database and migration policy

**Decision date:** 2026-11-21  
**Status:** Canonical architecture decision; rollout and data reconciliation remain gated.

## Single source of truth

All CUBI environments and modules use one PostgreSQL database:

- Supabase project: `CUBI-Platform-Core-DB`
- Project reference: `pbgosszuzemljgoccppk`
- Region: `eu-central-1`
- PostgreSQL major version: 17

Engineering, Enterprise, Personal Workbench, identity, administration, AI Workbench, projects, schedules, resources, documents, reports, settings, audit and history are logical domains within this one database. Environment and tenant separation is enforced by tenant identifiers, authorization and scoped data access—not by creating another database.

## Runtime connection contract

- Production and the canonical authenticated Preview must use `CONSTRUCTION_PM_DATABASE_URL` pointing to this project.
- `CONSTRUCTION_PM_SESSION_SECRET` is a separate server-only secret and must be at least 32 characters.
- Database credentials and connection strings must exist only in deployment secret stores. Never commit, print, expose to browser bundles or put them in issue descriptions.
- No module may introduce a new MySQL, SQLite, local-file or in-memory production persistence path. SQLite and fixtures remain test-only.
- Vercel and Render services must be configured against the same Supabase project before any signup or production write is enabled.

## Migration and retirement policy

1. Keep existing MySQL systems intact and read-only where practical while inventorying them.
2. Migrate all existing data into the canonical PostgreSQL database using repeatable, auditable migrations.
3. Reconcile source/target row counts, keys, foreign-key relationships, tenant ownership, nullability, checksums and domain-specific invariants.
4. Run application integration, concurrent-write, restart/read-after-write, backup/restore and security tests against PostgreSQL.
5. Switch all production and preview runtime connections to this project and verify the deployed commit and effective runtime configuration.
6. Only after successful reconciliation, verified backups, a rollback window and explicit owner approval may legacy MySQL be shut down or deleted.

No destructive migration, MySQL deletion, production deployment or production cutover is authorized by this document alone.

## Current verified state

The Supabase project is active and accepts SQL connections. At the initial inventory, the public schema contained the existing knowledge/assistant and organization-binding tables, but not the production identity, sessions or complete Engineering/Enterprise application schema. Render had no managed PostgreSQL instance. The inspected Vercel Preview environment had an empty database URL and session secret and was intentionally using fixture runtime.

Therefore, the database is selected and reachable, but **runtime convergence and historical data migration are not yet complete**. Do not enable public registration against a fixture deployment or claim durable production readiness until the runtime uses the canonical database and restart/read-after-write is proven.

## Migration ownership

The versioned registry in `src/construction_pm/deployment/migrations.py` is the application schema authority. New changes must be additive, versioned, checksummed and tested. Existing migration history must never be rewritten to disguise schema drift.
