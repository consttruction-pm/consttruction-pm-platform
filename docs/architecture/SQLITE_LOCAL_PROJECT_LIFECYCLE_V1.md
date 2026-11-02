# SQLite Local Project Lifecycle Repository v1

**Status:** First repository adapter slice; not a complete offline product database.
**Parent work:** #1680; architecture gate #1670.

## Purpose

Provide a production local-client SQLite adapter for the existing Python `ProjectRepository` protocol. It is intentionally separate from `PreviewProjectRepository` and preview/demo database markers.

## Contract

- Implements `ProjectRepository` from `application.project_lifecycle`.
- Stores tenant-scoped project metadata, project data revision, metadata/settings revision and memberships.
- Every list/get/update operation is membership-scoped.
- Project creation inserts the project and its initial owner membership in one transaction.
- Uses the existing `SQLiteTransactionManager`; nested operations use savepoints and caller-owned outer transactions are never committed or rolled back by the repository.
- Metadata updates use `settings_revision` and preserve the separate project data `revision`.
- Project start dates are canonical ISO Gregorian strings; `date_system` is presentation metadata only.
- Database schema version is recorded in SQLite `PRAGMA user_version` (version 1).

## Usage

A trusted local application host opens a persistent SQLite file and uses `build_sqlite_project_lifecycle_api` to compose this repository with the existing `ProjectLifecycleService` and `ProjectLifecycleAPI`. The host supplies its authenticated local session provider and offline-entitlement-aware authorization policy. Identity issuance and offline entitlement verification are not performed by this repository.

The same connection can be shared with other SQLite domain repositories and the durable outbox. The host must wrap a local domain mutation and outbox append in the same `SQLiteTransactionManager.transaction()` boundary; this class does not claim to implement that broader atomic workflow by itself.

## Not certified by this slice

- Full local domain database composition for activities, WBS, relationships, calendars, resources, costs, EVM and attachments.
- Signed offline identity/permission/entitlement provider.
- Atomic domain mutation plus durable outbox integration.
- Backup/restore, schema migration upgrades beyond version 1, crash recovery and native app packaging.
- Windows/Android/iOS offline device tests.
