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

For remote databases, both DSNs must target the same host/port/database but use different PostgreSQL usernames. The migration role creates tables/indexes/triggers. Grant the application role schema usage and SELECT/INSERT on `ai_learning_memory_records` and `ai_learning_memory_audit_events`; revoke UPDATE/DELETE. Runtime startup verifies these grants and refuses a remote runtime role with broader mutation rights. Local loopback integration tests may use one DSN for both roles.

When unset/disabled, the factory returns `None`; it never silently falls back to SQLite. Do not log either DSN. The runtime applies checked migrations using the migration connection, then opens a separate least-privilege application connection and leaves it idle after its startup checks. The deployment must close the runtime on graceful shutdown.

This repository configuration does not provision PostgreSQL or set provider backups. Production still requires a durable managed database, separate secret credentials, encrypted automated backups, restore drills, monitoring and an explicit policy mapping for learning-memory grants.
