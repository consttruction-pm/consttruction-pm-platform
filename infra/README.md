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
