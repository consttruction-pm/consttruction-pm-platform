# SQLite Local Application Runtime v1

**Status:** First full local application-composition slice; native packaging and full offline product acceptance remain open.
**Parent:** #1680; architecture decision #1670; implementation gate #1687.

## Product boundary

- Web remains online-only and uses its authenticated server-side Python composition.
- Windows Desktop and Flutter Mobile use this same Python application/domain composition with platform-native session/secure-storage hosts and local SQLite files.
- This module does not import Preview, WSGI, web UI or demo fixture packages.

## Composition

Module: `src/construction_pm/sqlite_local_runtime.py`.

`build_sqlite_local_application_runtime(connection, sessions, authorization_policy, rules_version, engine_version)` composes over one caller-owned SQLite connection:

- local ProjectRepository + existing ProjectLifecycleService/API;
- WBS, Activity Master, Relationships and Constraints;
- versioned project calendars, assignments, snapshots, exceptions and work-hour rules;
- schedule settings, immutable schedule snapshots and CalculationContext;
- resource assignments, periods, spreads and effective-dated capacity;
- baseline, cost-account and expense repositories;
- the existing Activity/WBS/Relationship/Calendar/Resource APIs;
- authoritative snapshot publication and the transport-independent SharedCoreRuntime.

The same SQLiteTransactionManager is passed to application services and snapshot publication. The host must create this composition once at startup and must not instantiate repositories inside a user mutation transaction; the existing SQLite repository constructors perform their schema initialization at startup.

## Calendar resolution

`build_sqlite_calendar_resolver_registry(scope, ...)` binds exact calendar ID+version records to the existing Shared Core resolver types. It reads immutable snapshots, strict weekly-work-hour rules, exception layers and exact base-calendar versions. Missing snapshots, invalid work-hour mappings, kind/system mismatch, inheritance cycles and unresolved parents fail closed. It contains no date arithmetic.

## Local scheduling workflow

1. Host authenticates the local actor and verifies its offline permission/entitlement.
2. Existing application APIs create/update project, WBS, activity, relationship and calendar records under the supplied AuthorizationContext.
3. Schedule settings are stored against the exact project revision.
4. `P6ScheduleSnapshotPublicationAPI.publish` performs fresh persisted reads and creates an immutable versioned snapshot/context in one SQLite transaction.
5. `runtime.schedule_runtime(scope)` creates the SharedCoreRuntime bound to the project's local exact-version calendar registry and resource-leveling resolver.
6. `schedule.query` runs the same `AuthoritativeScheduleQueryProvider` and Python Shared Core evaluator used by Web.

The native bridge must pass trusted AuthorizationContext and current project revision out-of-band. JSON input cannot grant identity, roles, permissions or a revision.

## Scope not certified by this slice

- Native Windows embedded Python package/installer/signing.
- Flutter Android/iOS embedded Python, native bridge and release pipelines.
- Complete durable outbox atomic integration, attachment binary storage, project-wide backup/restore and Undo/Redo.
- Full cost/baseline/expense application APIs and every project module's write workflow (the repositories are exposed for subsequent API composition).
- Signed offline session/entitlement provider and OS secure storage.
- Device/process-kill/offline restart tests and cross-runtime golden-result parity.
