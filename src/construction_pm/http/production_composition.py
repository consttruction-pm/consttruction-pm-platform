from __future__ import annotations

import os
from typing import Callable

from construction_pm.application.authorization import AuthorizationContext, AuthorizationPolicy
from construction_pm.calendar_exception_repository import CalendarExceptionRepository
from construction_pm.calendar_master_repository import CalendarMasterRepository
from construction_pm.calendar_snapshot_repository import CalendarSnapshotRepository
from construction_pm.calendar_work_hours_repository import CalendarWorkHourRepository
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.ai_action_boundary import AIToolPermissionAdapter
from construction_pm.ai_action_activity_tools import build_activity_create_runtime
from construction_pm.backend_p0.api import BackendP0API
from construction_pm.backend_p0.authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from construction_pm.backend_p0.schedule_query import ScheduleQueryAPI, ScheduleQueryApplicationService
from construction_pm.activity_master_repository import ActivityMasterRepository
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_formula_authority_api import P6FormulaAuthorityAPI
from construction_pm.p6_interchange_api import P6InterchangeAPI
from construction_pm.p6_layout_definition_api import P6LayoutDefinitionAPI
from construction_pm.p6_persisted_resource_leveling_resolver import build_persisted_resource_leveling_input_resolver
from construction_pm.p6_resource_capacity_read_api import P6ResourceCapacityReadAPI
from construction_pm.p6_resource_capacity_write_api import P6ResourceCapacityWriteAPI
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_schedule_snapshot_publication_api import P6ScheduleSnapshotPublicationAPI
from construction_pm.relationship_master_repository import RelationshipMasterRepository
from construction_pm.http.project_lifecycle_routes import Clock, ProjectLifecycleHttpRoutes
from construction_pm.ai_action_runtime import (
    AIActionRuntime,
    AIActionRuntimeError,
    AIActionTransactionManager,
)
from construction_pm.ai_assistant_orchestration import (
    AIChatProvider,
    AIAssistantTurnOrchestrator,
    OpenAICompatibleChatProvider,
    build_ai_chat_provider_from_environment,
)
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.schedule_calculation_context_repository import CalculationContextRepository
from construction_pm.schedule_input_snapshot_repository import ScheduleInputSnapshot, ScheduleInputSnapshotRepository
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput


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
    backend_p0_api: BackendP0API | None = None,
    p6_field_registry_api: P6FieldRegistryAPI | None = None,
    p6_layout_definition_api: P6LayoutDefinitionAPI | None = None,
    p6_formula_authority_api: P6FormulaAuthorityAPI | None = None,
    p6_calendar_read_api: P6CalendarReadAPI | None = None,
    p6_interchange_api: P6InterchangeAPI | None = None,
    clock: Clock | None = None,
    ai_action_runtime: AIActionRuntime | None = None,
    ai_action_permission_adapter: AIToolPermissionAdapter | None = None,
    ai_action_transaction_manager: AIActionTransactionManager | None = None,
    ai_assistant_provider: AIChatProvider | None = None,
    leveling_input_resolver: Callable[[ScheduleInputSnapshot, CalculationContext, CalendarResolverRegistry, AuthorizationContext], SchedulerLevelingInput | None] | None = None,
    resource_read_api: P6ResourceReadAPI | None = None,
    resource_write_api: P6ResourceWriteAPI | None = None,
    p6_resource_capacity_read_api: P6ResourceCapacityReadAPI | None = None,
    p6_resource_capacity_write_api: P6ResourceCapacityWriteAPI | None = None,
    resource_calendar_master_repository: CalendarMasterRepository | None = None,
    resource_calendar_snapshot_repository: CalendarSnapshotRepository | None = None,
    resource_calendar_exception_repository: CalendarExceptionRepository | None = None,
    resource_calendar_work_hours_repository: CalendarWorkHourRepository | None = None,
) -> ProjectLifecycleWsgiApp:
    """Compose the production-facing lifecycle WSGI seam.

    Deployment owns the outer server/runtime and calls this function with its
    concrete lifecycle/session dependencies. Schedule Query is wired here to
    the authoritative snapshot evaluator and persisted CalculationContext;
    HTTP transport remains separate from Shared Core calculations. The optional
    AI action runtime exposes proposal/approval/execution routes only when a
    deployment supplies its current grant provider, durable store, and real
    application-tool handlers. There is deliberately no permissive fallback.
    The assistant provider is wired only through an explicit dependency or
    CUBI_AI_ENABLED=true with server-only CUBI_AI_* environment configuration.
    """
    assistant_enabled = os.environ.get("CUBI_AI_ENABLED", "").strip().lower() in {
        "1", "true", "yes"
    }
    if ai_assistant_provider is None and assistant_enabled:
        ai_assistant_provider = build_ai_chat_provider_from_environment()

    resource_resolver_dependencies = (
        resource_read_api,
        resource_calendar_master_repository,
        resource_calendar_snapshot_repository,
        resource_calendar_exception_repository,
        resource_calendar_work_hours_repository,
    )
    if leveling_input_resolver is not None and any(
        dependency is not None for dependency in resource_resolver_dependencies
    ):
        raise ValueError("RESOURCE_LEVELING_RESOLVER_CONFIGURATION_CONFLICT")
    if any(dependency is not None for dependency in resource_resolver_dependencies):
        if not all(dependency is not None for dependency in resource_resolver_dependencies):
            raise ValueError("RESOURCE_LEVELING_RESOLVER_DEPENDENCIES_INCOMPLETE")
        leveling_input_resolver = build_persisted_resource_leveling_input_resolver(
            resource_read_api=resource_read_api,
            calendar_master_repository=resource_calendar_master_repository,
            calendar_snapshot_repository=resource_calendar_snapshot_repository,
            calendar_exception_repository=resource_calendar_exception_repository,
            calendar_work_hours_repository=resource_calendar_work_hours_repository,
        )
    provider = AuthoritativeScheduleQueryProvider(
        snapshot_repository=snapshot_repository,
        calendar_registry_factory=calendar_registry_factory,
        calculation_context_repository=calculation_context_repository,
        leveling_input_resolver=leveling_input_resolver,
    )
    schedule_query_api = ScheduleQueryAPI(
        ScheduleQueryApplicationService(
            provider=provider,
            authorization_policy=authorization_policy,
        )
    )
    runtime_config_requested = (
        ai_action_permission_adapter is not None
        or ai_action_transaction_manager is not None
    )
    if ai_action_runtime is not None and runtime_config_requested:
        raise AIActionRuntimeError("AI_ACTION_RUNTIME_CONFIGURATION_CONFLICT")
    if runtime_config_requested:
        if (
            ai_action_permission_adapter is None
            or ai_action_transaction_manager is None
            or activity_master_repository is None
        ):
            raise AIActionRuntimeError("AI_ACTION_RUNTIME_DEPENDENCIES_INCOMPLETE")
        ai_action_runtime = build_activity_create_runtime(
            activity_master_repository=activity_master_repository,
            authorization_policy=authorization_policy,
            permission_adapter=ai_action_permission_adapter,
            transaction_manager=ai_action_transaction_manager,
            clock=None if clock is None else clock.now,
        )

    ai_assistant_orchestrator = None
    if ai_assistant_provider is not None:
        if ai_action_runtime is None:
            raise AIActionRuntimeError("AI_ASSISTANT_ACTION_RUNTIME_REQUIRED")
        ai_assistant_orchestrator = AIAssistantTurnOrchestrator(
            provider=ai_assistant_provider,
            action_runtime=ai_action_runtime,
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
    routes = ProjectLifecycleHttpRoutes(
        lifecycle_api,
        clock=clock,
        p6_activity_master_api=activity_master_api,
        p6_relationship_api=relationship_api,
        p6_schedule_snapshot_api=schedule_snapshot_publication_api,
        p6_field_registry_api=p6_field_registry_api,
        p6_layout_definition_api=p6_layout_definition_api,
        p6_formula_authority_api=p6_formula_authority_api,
        p6_calendar_read_api=p6_calendar_read_api,
        p6_interchange_api=p6_interchange_api,
        p6_resource_read_api=resource_read_api,
        p6_resource_write_api=resource_write_api,
        p6_resource_capacity_read_api=p6_resource_capacity_read_api,
        p6_resource_capacity_write_api=p6_resource_capacity_write_api,
        backend_p0_api=backend_p0_api,
        schedule_query_api=schedule_query_api,
        ai_action_runtime=ai_action_runtime,
        ai_assistant_orchestrator=ai_assistant_orchestrator,
    )
    return ProjectLifecycleWsgiApp(routes)


__all__ = ["build_project_lifecycle_wsgi_app"]