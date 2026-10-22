from __future__ import annotations

from typing import Callable

from construction_pm.application.authorization import AuthorizationPolicy
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.api import BackendP0API
from construction_pm.backend_p0.authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from construction_pm.backend_p0.schedule_query import ScheduleQueryAPI, ScheduleQueryApplicationService
from construction_pm.activity_master_repository import ActivityMasterRepository
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_schedule_snapshot_publication_api import P6ScheduleSnapshotPublicationAPI
from construction_pm.p6_resource_rate_api import P6ResourceRateAPI
from construction_pm.p6_resource_rate_repository import P6ResourceRateRepository
from construction_pm.p6_relationship_lag_calendar_api import P6RelationshipLagCalendarAPI
from construction_pm.relationship_master_repository import RelationshipMasterRepository
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
    activity_master_repository: ActivityMasterRepository | None = None,
    relationship_master_repository: RelationshipMasterRepository | None = None,
    schedule_snapshot_publication_api: P6ScheduleSnapshotPublicationAPI | None = None,
    resource_rate_repository: P6ResourceRateRepository | None = None,
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
    activity_master_api = (
        None
        if activity_master_repository is None
        else P6ActivityMasterAPI(activity_master_repository, authorization_policy)
    )
    relationship_api = (
        None
        if relationship_master_repository is None
        else P6RelationshipAPI(relationship_master_repository, authorization_policy)
    )
    # Share the exact capacity repository with the authoritative snapshot composer.
    # When callers pass a precomposed publication API, infer its persisted rate
    # repository unless one was explicitly supplied. Reject split-brain wiring.
    publication_composer = (
        None
        if schedule_snapshot_publication_api is None
        else getattr(
            getattr(schedule_snapshot_publication_api, "publisher", None),
            "composer",
            None,
        )
    )
    composer_rate_repository = getattr(publication_composer, "resource_rate_repository", None)
    if resource_rate_repository is None:
        resource_rate_repository = composer_rate_repository
    elif publication_composer is not None and composer_rate_repository is not resource_rate_repository:
        raise ValueError("RESOURCE_RATE_REPOSITORY_WIRING_MISMATCH")
    resource_rate_api = (
        None
        if resource_rate_repository is None
        else P6ResourceRateAPI(resource_rate_repository, authorization_policy)
    )
    calendar_assignment_repository = getattr(
        publication_composer, "calendar_assignment_repository", None
    )
    relationship_lag_calendar_api = (
        None
        if calendar_assignment_repository is None
        else P6RelationshipLagCalendarAPI(
            calendar_assignment_repository, authorization_policy
        )
    )
    routes = ProjectLifecycleHttpRoutes(
        lifecycle_api,
        clock=clock,
        p6_activity_master_api=activity_master_api,
        p6_relationship_api=relationship_api,
        p6_schedule_snapshot_api=schedule_snapshot_publication_api,
        p6_resource_rate_api=resource_rate_api,
        p6_relationship_lag_calendar_api=relationship_lag_calendar_api,
        backend_p0_api=backend_p0_api,
        schedule_query_api=schedule_query_api,
    )
    return ProjectLifecycleWsgiApp(routes)


__all__ = ["build_project_lifecycle_wsgi_app"]