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
