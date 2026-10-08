from __future__ import annotations

from typing import Callable

from construction_pm.application.authorization import AuthorizationPolicy
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.api import BackendP0API
from construction_pm.backend_p0.authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from construction_pm.backend_p0.schedule_query import ScheduleQueryAPI, ScheduleQueryApplicationService
from construction_pm.http.project_lifecycle_routes import Clock, ProjectLifecycleHttpRoutes
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.schedule_calculation_context_repository import CalculationContextRepository
from construction_pm.schedule_input_snapshot_repository import ScheduleInputSnapshotRepository
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry


def build_project_lifecycle_wsgi_app(
    *,
    lifecycle_api: ProjectLifecycleAPI,
    snapshot_repository: ScheduleInputSnapshotRepository,
    calendar_registry_factory: Callable[[], CalendarResolverRegistry],
    calculation_context_repository: CalculationContextRepository,
    authorization_policy: AuthorizationPolicy,
    backend_p0_api: BackendP0API | None = None,
    clock: Clock | None = None,
) -> ProjectLifecycleWsgiApp:
    """Compose the production-facing lifecycle WSGI seam.

    Deployment owns the outer server/runtime and calls this function with its
    concrete lifecycle/session dependencies. Schedule Query is wired here to
    the authoritative snapshot evaluator and persisted CalculationContext;
    HTTP transport remains separate from Shared Core calculations.
    """
    provider = AuthoritativeScheduleQueryProvider(
        snapshot_repository=snapshot_repository,
        calendar_registry_factory=calendar_registry_factory,
        calculation_context_repository=calculation_context_repository,
    )
    schedule_query_api = ScheduleQueryAPI(
        ScheduleQueryApplicationService(
            provider=provider,
            authorization_policy=authorization_policy,
        )
    )
    routes = ProjectLifecycleHttpRoutes(
        lifecycle_api,
        clock=clock,
        backend_p0_api=backend_p0_api,
        schedule_query_api=schedule_query_api,
    )
    return ProjectLifecycleWsgiApp(routes)


__all__ = ["build_project_lifecycle_wsgi_app"]