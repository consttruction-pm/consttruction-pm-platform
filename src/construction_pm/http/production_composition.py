from __future__ import annotations

import os
from typing import Callable, Mapping

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
from construction_pm.activity_progress_history import ActivityProgressHistoryRepository
from construction_pm.backend_p0.transactions import TransactionManager
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_activity_progress_api import P6ActivityProgressAPI
from construction_pm.p6_wbs_master_api import P6WBSMasterAPI
from construction_pm.p6_calendar_api import P6CalendarAPI
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI
from construction_pm.p6_calendar_usage_api import P6CalendarUsageAPI
from construction_pm.p6_baseline_api import P6BaselineAPI
from construction_pm.p6_baseline_update_api import P6BaselineUpdateAPI
from construction_pm.p6_baseline_assignment_api import P6BaselineAssignmentAPI
from construction_pm.p6_baseline_conversion_api import P6BaselineConversionAPI
from construction_pm.p6_baseline_capture_api import P6BaselineCaptureAPI
from construction_pm.p6_earned_value_read_model_api import P6EarnedValueReadModelAPI
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_udf_value_api import P6UserDefinedFieldValueAPI
from construction_pm.p6_formula_authority_api import P6FormulaAuthorityAPI
from construction_pm.p6_formula_column import P6FormulaColumnAPI
from construction_pm.p6_interchange_api import P6InterchangeAPI
from construction_pm.p6_layout_definition_api import P6LayoutDefinitionAPI
from construction_pm.p6_persisted_resource_leveling_resolver import build_persisted_resource_leveling_input_resolver
from construction_pm.p6_resource_capacity_read_api import P6ResourceCapacityReadAPI
from construction_pm.p6_resource_capacity_write_api import P6ResourceCapacityWriteAPI
from construction_pm.p6_resource_rate_read_api import P6ResourceRateReadAPI
from construction_pm.p6_resource_rate_write_api import P6ResourceRateWriteAPI
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_role_api import P6RoleAPI
from construction_pm.p6_role_details_api import P6RoleDetailsAPI
from construction_pm.p6_resource_master_api import P6ResourceAPI
from construction_pm.p6_expense_api import P6ExpenseAPI
from construction_pm.p6_cost_account_api import P6CostAccountAPI
from construction_pm.p6_financial_period_api import P6FinancialPeriodAPI
from construction_pm.p6_issue_api import P6IssueAPI
from construction_pm.p6_activity_step_api import P6ActivityStepReadAPI
from construction_pm.document_api import DocumentAPI
from construction_pm.budget_api import BudgetAPI
from construction_pm.cost_api import CostAPI
from construction_pm.risk_api import RiskAPI
from construction_pm.report_api import ReportAPI
from construction_pm.administration_api import AdministrationAPI
from construction_pm.backup_api import BackupAPI
from construction_pm.exchange_api import ExchangeAPI
from construction_pm.threshold_api import ThresholdAPI
from construction_pm.p6_schedule_snapshot_publication_api import P6ScheduleSnapshotPublicationAPI
from construction_pm.relationship_master_repository import RelationshipMasterRepository
from construction_pm.wbs_master_repository import WBSMasterRepository
from construction_pm.http.project_lifecycle_routes import Clock, ProjectLifecycleHttpRoutes
from construction_pm.form_builder_api import FormBuilderAPI
from construction_pm.ai_action_runtime import (
    AIActionRuntime,
    AIActionRuntimeError,
    AIActionTransactionManager,
)
from construction_pm.ai_assistant_orchestration import (
    AIChatProvider,
    AIAssistantTurnOrchestrator,
    OpenAICompatibleChatProvider,
)
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.http.operational import OperationalMiddleware
from construction_pm.production_readiness import (
    ReadinessService,
    StructuredEventLogger,
    build_readiness_service,
)
from construction_pm.backend_p0.workspace_read import WorkspaceControlRoomReadService
from construction_pm.backend_p0.workspace_read_provider import PersistedWorkspaceReadProvider
from construction_pm.backend_p0.authoritative_schedule_facts import PublishedScheduleFactsProvider
from construction_pm.tracking_read_model import (
    TrackingReadAPI,
    TrackingReadModelService,
    TrackingSources,
)
from construction_pm.p6_resource_assignment_repository import P6ResourceAssignmentRepository
from construction_pm.p6_resource_master_repository import P6ResourceRepository
from construction_pm.schedule_calculation_context_repository import CalculationContextRepository
from construction_pm.schedule_input_snapshot_repository import ScheduleInputSnapshot, ScheduleInputSnapshotRepository
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.leveling_cost_recalculation import LevelingCostInputs


def build_project_lifecycle_wsgi_app(
    *,
    lifecycle_api: ProjectLifecycleAPI,
    snapshot_repository: ScheduleInputSnapshotRepository,
    calendar_registry_factory: Callable[[], CalendarResolverRegistry],
    calculation_context_repository: CalculationContextRepository,
    authorization_policy: AuthorizationPolicy,
    activity_master_repository: ActivityMasterRepository | None = None,
    activity_progress_history_repository: ActivityProgressHistoryRepository | None = None,
    activity_progress_transaction_manager: TransactionManager | None = None,
    wbs_master_repository: WBSMasterRepository | None = None,
    workspace_read_v2_service: WorkspaceControlRoomReadService | None = None,
    relationship_master_repository: RelationshipMasterRepository | None = None,
    schedule_snapshot_publication_api: P6ScheduleSnapshotPublicationAPI | None = None,
    backend_p0_api: BackendP0API | None = None,
    p6_field_registry_api: P6FieldRegistryAPI | None = None,
    p6_udf_value_api: P6UserDefinedFieldValueAPI | None = None,
    p6_layout_definition_api: P6LayoutDefinitionAPI | None = None,
    p6_formula_authority_api: P6FormulaAuthorityAPI | None = None,
    p6_formula_column_api: P6FormulaColumnAPI | None = None,
    p6_calendar_read_api: P6CalendarReadAPI | None = None,
    p6_calendar_usage_api: P6CalendarUsageAPI | None = None,
    p6_calendar_api: P6CalendarAPI | None = None,
    p6_baseline_api: P6BaselineAPI | None = None,
    p6_baseline_update_api: P6BaselineUpdateAPI | None = None,
    p6_baseline_assignment_api: P6BaselineAssignmentAPI | None = None,
    p6_baseline_conversion_api: P6BaselineConversionAPI | None = None,
    p6_baseline_capture_api: P6BaselineCaptureAPI | None = None,
    p6_earned_value_read_api: P6EarnedValueReadModelAPI | None = None,
    p6_interchange_api: P6InterchangeAPI | None = None,
    p6_role_api: P6RoleAPI | None = None,
    p6_role_details_api: P6RoleDetailsAPI | None = None,
    p6_resource_api: P6ResourceAPI | None = None,
    p6_expense_api: P6ExpenseAPI | None = None,
    p6_cost_account_api: P6CostAccountAPI | None = None,
    p6_financial_period_api: P6FinancialPeriodAPI | None = None,
    p6_issue_api: P6IssueAPI | None = None,
    p6_activity_step_api: P6ActivityStepReadAPI | None = None,
    document_api: DocumentAPI | None = None,
    tracking_read_api: TrackingReadAPI | None = None,
    tracking_resource_assignment_repository: P6ResourceAssignmentRepository | None = None,
    tracking_resource_repository: P6ResourceRepository | None = None,
    budget_api: BudgetAPI | None = None,
    cost_api: CostAPI | None = None,
    threshold_api: ThresholdAPI | None = None,
    risk_api: RiskAPI | None = None,
    report_api: ReportAPI | None = None,
    administration_api: AdministrationAPI | None = None,
    exchange_api: ExchangeAPI | None = None,
    backup_api: BackupAPI | None = None,
    clock: Clock | None = None,
    ai_action_runtime: AIActionRuntime | None = None,
    ai_action_permission_adapter: AIToolPermissionAdapter | None = None,
    ai_action_transaction_manager: AIActionTransactionManager | None = None,
    ai_assistant_provider: AIChatProvider | None = None,
    leveling_input_resolver: Callable[[ScheduleInputSnapshot, CalculationContext, CalendarResolverRegistry, AuthorizationContext], SchedulerLevelingInput | None] | None = None,
    cost_inputs_resolver: Callable[[ScheduleInputSnapshot, CalculationContext, AuthorizationContext], LevelingCostInputs | None] | None = None,
    resource_read_api: P6ResourceReadAPI | None = None,
    resource_write_api: P6ResourceWriteAPI | None = None,
    p6_resource_capacity_read_api: P6ResourceCapacityReadAPI | None = None,
    p6_resource_capacity_write_api: P6ResourceCapacityWriteAPI | None = None,
    p6_resource_rate_read_api: P6ResourceRateReadAPI | None = None,
    p6_resource_rate_write_api: P6ResourceRateWriteAPI | None = None,
    resource_calendar_master_repository: CalendarMasterRepository | None = None,
    resource_calendar_snapshot_repository: CalendarSnapshotRepository | None = None,
    resource_calendar_exception_repository: CalendarExceptionRepository | None = None,
    resource_calendar_work_hours_repository: CalendarWorkHourRepository | None = None,
    form_builder_api: FormBuilderAPI | None = None,
    knowledge_database: str | None = None,
    knowledge_plan_port: object | None = None,
    readiness_service: ReadinessService | None = None,
    readiness_probes: Mapping[str, Callable[[], object]] | None = None,
    request_logger: StructuredEventLogger | None = None,
    environment: Mapping[str, str] | None = None,
    operational_endpoints: bool = True,
) -> ProjectLifecycleWsgiApp:
    """Compose the production-facing lifecycle WSGI seam.

    Deployment owns the outer server/runtime and calls this function with its
    concrete lifecycle/session dependencies. Schedule Query is wired here to
    the authoritative snapshot evaluator and persisted CalculationContext;
    HTTP transport remains separate from Shared Core calculations. The optional
    AI action runtime exposes proposal/approval/execution routes only when a
    deployment supplies its current grant provider, durable store, and real
    application-tool handlers. There is deliberately no permissive fallback.
    The optional ``cost_inputs_resolver`` is the application-bound seam that
    supplies persisted, effective-dated rate facts and assignments when a
    schedule requests post-leveling cost recalculation; the evaluator itself
    never reads a repository.
    The assistant provider is wired only through an explicit dependency or
    CUBI_AI_ENABLED=true with server-only CUBI_AI_* environment configuration.
    """
    assistant_enabled = os.environ.get("CUBI_AI_ENABLED", "").strip().lower() in {
        "1", "true", "yes"
    }
    if ai_assistant_provider is None and assistant_enabled:
        ai_assistant_provider = OpenAICompatibleChatProvider.from_environment()

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
        cost_inputs_resolver=cost_inputs_resolver,
    )
    schedule_query_api = ScheduleQueryAPI(
        ScheduleQueryApplicationService(
            provider=provider,
            authorization_policy=authorization_policy,
        )
    )
    if tracking_read_api is None and activity_master_repository is not None:
        # Tracking reads the published schedule FACT projection and persisted
        # assignment facts; it never re-runs CPM or money calculations.
        tracking_read_api = TrackingReadAPI(
            TrackingReadModelService(
                schedule_facts_provider=PublishedScheduleFactsProvider(
                    snapshot_repository, provider
                ),
                sources=TrackingSources(
                    activity_repository=activity_master_repository,
                    wbs_repository=wbs_master_repository,
                    resource_assignment_repository=tracking_resource_assignment_repository,
                    resource_repository=tracking_resource_repository,
                ),
            ),
            authorization_policy,
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
    if (
        activity_progress_history_repository is not None
        or activity_progress_transaction_manager is not None
    ) and (
        activity_master_api is None
        or activity_progress_history_repository is None
        or activity_progress_transaction_manager is None
    ):
        raise ValueError("ACTIVITY_PROGRESS_HISTORY_DEPENDENCIES_INCOMPLETE")
    activity_progress_api = (
        None
        if activity_progress_history_repository is None
        else P6ActivityProgressAPI(
            activity_api=activity_master_api,  # type: ignore[arg-type]
            history_repository=activity_progress_history_repository,
            authorization_policy=authorization_policy,
            relationship_repository=relationship_master_repository,
            activity_repository=activity_master_repository,
            transaction_manager=activity_progress_transaction_manager,
        )
    )
    wbs_master_api = (
        None
        if wbs_master_repository is None
        else P6WBSMasterAPI(wbs_master_repository, authorization_policy)
    )
    relationship_api = (
        None
        if relationship_master_repository is None
        else P6RelationshipAPI(
            relationship_master_repository,
            authorization_policy,
            activity_master_repository,
        )
    )
    if (
        workspace_read_v2_service is None
        and activity_master_repository is not None
        and wbs_master_repository is not None
    ):
        workspace_read_v2_service = WorkspaceControlRoomReadService(
            provider=PersistedWorkspaceReadProvider(
                activity_repository=activity_master_repository,
                wbs_repository=wbs_master_repository,
                relationship_repository=relationship_master_repository,
            ),
            authorization_policy=authorization_policy,
        )
    routes = ProjectLifecycleHttpRoutes(
        lifecycle_api,
        clock=clock,
        p6_activity_master_api=activity_master_api,
        p6_activity_progress_api=activity_progress_api,
        p6_wbs_master_api=wbs_master_api,
        workspace_read_v2_service=workspace_read_v2_service,
        p6_relationship_api=relationship_api,
        p6_schedule_snapshot_api=schedule_snapshot_publication_api,
        p6_field_registry_api=p6_field_registry_api,
        p6_udf_value_api=p6_udf_value_api,
        p6_layout_definition_api=p6_layout_definition_api,
        p6_formula_authority_api=p6_formula_authority_api,
        p6_formula_column_api=p6_formula_column_api,
        p6_calendar_read_api=p6_calendar_read_api,
        p6_calendar_usage_api=p6_calendar_usage_api,
        p6_calendar_api=p6_calendar_api,
        p6_baseline_api=p6_baseline_api,
        p6_baseline_update_api=p6_baseline_update_api,
        p6_baseline_assignment_api=p6_baseline_assignment_api,
        p6_baseline_conversion_api=p6_baseline_conversion_api,
        p6_baseline_capture_api=p6_baseline_capture_api,
        p6_earned_value_read_api=p6_earned_value_read_api,
        p6_interchange_api=p6_interchange_api,
        p6_role_api=p6_role_api,
        p6_role_details_api=p6_role_details_api,
        p6_resource_api=p6_resource_api,
        p6_expense_api=p6_expense_api,
        p6_cost_account_api=p6_cost_account_api,
        p6_financial_period_api=p6_financial_period_api,
        p6_issue_api=p6_issue_api,
        p6_activity_step_api=p6_activity_step_api,
        document_api=document_api,
        tracking_read_api=tracking_read_api,
        budget_api=budget_api,
        cost_api=cost_api,
        threshold_api=threshold_api,
        risk_api=risk_api,
        report_api=report_api,
        administration_api=administration_api,
        exchange_api=exchange_api,
        backup_api=backup_api,
        p6_resource_read_api=resource_read_api,
        p6_resource_write_api=resource_write_api,
        p6_resource_capacity_read_api=p6_resource_capacity_read_api,
        p6_resource_capacity_write_api=p6_resource_capacity_write_api,
        p6_resource_rate_read_api=p6_resource_rate_read_api,
        p6_resource_rate_write_api=p6_resource_rate_write_api,
        backend_p0_api=backend_p0_api,
        schedule_query_api=schedule_query_api,
        ai_action_runtime=ai_action_runtime,
        ai_assistant_orchestrator=ai_assistant_orchestrator,
        form_builder_api=form_builder_api,
    )
    app: object = ProjectLifecycleWsgiApp(routes)
    if knowledge_database:
        # Mounted in front of the lifecycle application: the middleware answers
        # only /api/knowledge* and /api/projects/{id}/knowledge and delegates
        # everything else to the unchanged application behind it.
        from construction_pm.knowledge.runtime import build_knowledge_runtime

        app = build_knowledge_runtime(
            app,
            policy=authorization_policy,
            lifecycle_api=lifecycle_api,
            database=knowledge_database,
            plan_port=knowledge_plan_port,
            clock=None if clock is None else clock.now,
        ).app
    if operational_endpoints or request_logger is not None:
        if readiness_service is None and operational_endpoints:
            readiness_service = build_readiness_service(
                os.environ if environment is None else environment,
                probes=readiness_probes,
            )
        app = OperationalMiddleware(
            app,
            readiness=readiness_service,
            logger=request_logger,
        )
    return app


__all__ = ["build_project_lifecycle_wsgi_app"]