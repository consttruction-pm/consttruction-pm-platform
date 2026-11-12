"""Full-stack local preview runtime.

The runtime composes the real HTTP routes, the real SQLite repositories, the
real project lifecycle boundary and the Shared Domain/Calculation Core. The
only preview-specific pieces are the guarded demo database, demo sessions and
curated fixture data. No scheduling is reimplemented here.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.ai_action_activity_tools import (
    SQLiteAIActionExecutionIdempotencyStore,
    build_activity_create_tool,
)
from construction_pm.ai_action_project_plan_tools import build_project_plan_create_tool
from construction_pm.ai_action_runtime import AIActionProposal, AIActionRuntime, SQLiteAIActionRuntimeStore
from construction_pm.ai_assistant_orchestration import OpenAICompatibleChatProvider
from construction_pm.application.authorization import (
    AuthorizationContext,
    RoleBasedAuthorizationPolicy,
    default_project_policy,
)
from construction_pm.application.project_lifecycle import (
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.authoritative_schedule_input_composer import (
    AuthoritativeScheduleInputComposer,
)
from construction_pm.backend_p0.api import BackendP0API
from construction_pm.backend_p0.application import BackendP0ApplicationService
from construction_pm.backend_p0.authoritative_schedule_facts import (
    PublishedScheduleFactsProvider,
)
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.repository import InMemoryBackendP0Repository
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.backend_p0.workspace_read import WorkspaceControlRoomReadService
from construction_pm.backend_p0.workspace_read_provider import (
    PersistedWorkspaceReadProvider,
    WorkspaceScheduleFactsProvider,
)
from construction_pm.calendar_exception_kernel import (
    CalendarExceptionKernelError,
    persisted_exception_to_kernel,
)
from construction_pm.calendar_exception_repository import (
    SQLiteCalendarExceptionRepository,
)
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import (
    SQLiteCalendarSnapshotRepository,
)
from construction_pm.calendar_work_hours_repository import (
    SQLiteCalendarWorkHourRepository,
)
from construction_pm.p6_versioned_resource_calendar_resolver import (
    apply_weekly_work_hour_rules,
)
from construction_pm.constraint_master_repository import (
    SQLiteConstraintMasterRepository,
)
from construction_pm.form_builder_api import FormBuilderAPI
from construction_pm.form_builder_repository import SQLiteFormBuilderRepository
from construction_pm.form_builder_templates import seed_organization_library
from construction_pm.preview.form_bindings import PreviewFormBindingProvider, PreviewFormDirectory
from construction_pm.http.production_composition import (
    build_project_lifecycle_wsgi_app,
)
from construction_pm.http.project_lifecycle_routes import Clock
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.p6_earned_value_read_model import (
    P6EarnedValueReadModelError,
    P6EarnedValueReadModelService,
)
from construction_pm.p6_earned_value_read_model_api import P6EarnedValueReadModelAPI
from construction_pm.p6_activity_period_actual_repository import (
    SQLiteP6ActivityPeriodActualRepository,
)
from construction_pm.p6_cost_account_api import P6CostAccountAPI
from construction_pm.p6_cost_account_repository import (
    P6CostAccountApplicationService,
    SQLiteP6CostAccountRepository,
)
from construction_pm.p6_expense_api import P6ExpenseAPI
from construction_pm.p6_expense_repository import (
    P6ExpenseApplicationService,
    SQLiteP6ExpenseRepository,
)
from construction_pm.p6_financial_period_api import P6FinancialPeriodAPI
from construction_pm.p6_issue_api import P6IssueAPI
from construction_pm.p6_issue_repository import SQLiteP6IssueRepository
from construction_pm.document_api import DocumentAPI
from construction_pm.document_application import DocumentApplicationService
from construction_pm.document_persistence import (
    RolePermissionDocumentLifecycleAuthorizer,
    SQLiteDocumentStore,
)
from construction_pm.budget_api import BudgetAPI
from construction_pm.budget_application import BudgetApplicationService
from construction_pm.budget_persistence import SQLiteBudgetStore
from construction_pm.p6_financial_period_repository import (
    P6FinancialPeriodApplicationService,
    SQLiteP6FinancialPeriodRepository,
)
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_baseline_activity_repository import (
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_api import P6BaselineAPI
from construction_pm.p6_baseline_assignment import (
    P6BaselineAssignmentService,
    SQLiteP6BaselineRoleAssignmentRepository,
)
from construction_pm.p6_baseline_assignment_api import P6BaselineAssignmentAPI
from construction_pm.p6_baseline_conversion import P6BaselineConversionService
from construction_pm.p6_baseline_conversion_api import P6BaselineConversionAPI
from construction_pm.p6_baseline_repository import (
    P6BaselineApplicationService,
    SQLiteP6BaselineRepository,
)
from construction_pm.p6_baseline_update import P6BaselineUpdateService
from construction_pm.p6_baseline_update_api import P6BaselineUpdateAPI
from construction_pm.p6_calendar_api import P6CalendarAPI
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI
from construction_pm.p6_current_activity_value_repository import (
    P6CurrentActivityApplicationService,
    SQLiteP6CurrentActivityRepository,
)
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
    SQLiteP6FieldRegistryRepository,
)
from construction_pm.p6_formula_authority_api import P6FormulaAuthorityAPI
from construction_pm.p6_formula_column import P6FormulaColumnAPI, P6FormulaColumnService
from construction_pm.p6_formula_definition_repository import (
    P6FormulaDefinitionApplicationService,
    SQLiteP6FormulaDefinitionRepository,
)
from construction_pm.p6_interchange_api import P6InterchangeAPI
from construction_pm.p6_layout_definition_api import P6LayoutDefinitionAPI
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    SQLiteP6LayoutRepository,
)
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingRegistryApplicationService,
    P6MappingStatus,
    PersistedP6Mapping,
    SQLiteP6MappingRegistryRepository,
)
from construction_pm.p6_primavera_xml_codec import P6PrimaveraXmlCodec
from construction_pm.p6_resource_capacity_read_api import P6ResourceCapacityReadAPI
from construction_pm.p6_resource_capacity_write_api import P6ResourceCapacityWriteAPI
from construction_pm.p6_resource_capacity_repository import (
    P6ResourceCapacityApplicationService,
    P6ResourceCapacityRecord,
    SQLiteP6ResourceCapacityRepository,
)
from construction_pm.p6_resource_rate_read_api import P6ResourceRateReadAPI
from construction_pm.p6_resource_rate_write_api import P6ResourceRateWriteAPI
from construction_pm.p6_resource_rate_repository import (
    P6ResourceRateApplicationService,
    P6ResourceRateRecord,
    SQLiteP6ResourceRateRepository,
)
from construction_pm.resources.rate_facts import ResourceRateFact
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_role_api import P6RoleAPI
from construction_pm.p6_role_details_api import P6RoleDetailsAPI
from construction_pm.p6_role_dictionary_repository import (
    SQLiteP6RoleDictionaryRepository,
)
from construction_pm.p6_role_repository import SQLiteP6RoleRepository
from construction_pm.p6_resource_master_api import P6ResourceAPI
from construction_pm.p6_resource_master_repository import (
    P6Resource,
    SQLiteP6ResourceRepository,
)
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.p6_schedule_snapshot_publication_api import (
    P6ScheduleSnapshotPublicationAPI,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    SQLiteP6UserDefinedFieldRepository,
)
from construction_pm.project_schedule_settings_repository import (
    ProjectScheduleSettings,
    SQLiteProjectScheduleSettingsRepository,
)
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.resources.max_units_time import ResourceMaxUnitsTime
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
)
from construction_pm.schedule_snapshot_publisher import (
    AuthoritativeScheduleSnapshotPublisher,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.calendar_exception_overlay import CalendarExceptionLayers
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
)

from .fixtures import (
    CURATED_FIELD_IDS,
    DEFAULT_CALENDAR_VERSION,
    DEFAULT_PROJECT_LEVELING_PRIORITY,
    DEMO_PROJECTS,
    LAYOUT_COLUMNS,
    LAYOUT_SCOPE,
    LAYOUT_VIEW,
    REGISTRY_VERSION,
    DemoProjectFixture,
)
from .storage import (
    DEMO_PROJECT_MEMBER_USER_IDS,
    PREVIEW_SEED_VERSION,
    PREVIEW_TENANT_ID,
    PreviewDatabaseError,
    PreviewProjectRepository,
    PreviewSessionRepository,
    PreviewStore,
    open_preview_database,
)


PREVIEW_RULES_VERSION = "cubi-preview-rules.v1"
PREVIEW_ENGINE_VERSION = "cubi-preview-engine.v1"
PREVIEW_DEFAULT_CALENDAR_NAME = "Project working calendar (Mon-Fri)"
PREVIEW_DEFAULT_WORKING_WEEKDAYS = frozenset({0, 1, 2, 3, 4})


class PreviewRuntimeError(RuntimeError):
    """Raised when the preview cannot be composed safely."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


class PreviewClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass
class PreviewRepositories:
    activities: SQLiteActivityMasterRepository
    wbs: SQLiteWBSMasterRepository
    relationships: SQLiteRelationshipMasterRepository
    constraints: SQLiteConstraintMasterRepository
    calendars: SQLiteCalendarMasterRepository
    calendar_assignments: SQLiteCalendarAssignmentRepository
    calendar_snapshots: SQLiteCalendarSnapshotRepository
    calendar_exceptions: SQLiteCalendarExceptionRepository
    calendar_work_hours: SQLiteCalendarWorkHourRepository
    resource_assignments: SQLiteP6ResourceAssignmentRepository
    resource_periods: SQLiteP6ResourceAssignmentPeriodRepository
    resource_assignment_service: P6ResourceAssignmentApplicationService
    resource_period_service: P6ResourceAssignmentPeriodApplicationService
    resource_spread_service: P6ResourceSpreadApplicationService
    capacities: SQLiteP6ResourceCapacityRepository
    capacity_service: P6ResourceCapacityApplicationService
    rates: SQLiteP6ResourceRateRepository
    rate_service: P6ResourceRateApplicationService
    settings: SQLiteProjectScheduleSettingsRepository
    fields: SQLiteP6FieldRegistryRepository
    field_service: P6FieldRegistryApplicationService
    formula_definitions: SQLiteP6FormulaDefinitionRepository
    formula_definition_service: P6FormulaDefinitionApplicationService
    formula_column_service: P6FormulaColumnService
    udfs: SQLiteP6UserDefinedFieldRepository
    udf_service: P6UserDefinedFieldApplicationService
    mappings: SQLiteP6MappingRegistryRepository
    mapping_service: P6MappingRegistryApplicationService
    layouts: SQLiteP6LayoutRepository
    snapshots: SQLiteScheduleInputSnapshotRepository
    contexts: SQLiteCalculationContextRepository
    baselines: SQLiteP6BaselineRepository
    baseline_activities: SQLiteP6BaselineActivityRepository
    baseline_assignments: SQLiteP6BaselineRoleAssignmentRepository
    current_activity_values: SQLiteP6CurrentActivityRepository
    current_activity_service: P6CurrentActivityApplicationService
    roles: SQLiteP6RoleRepository
    role_dictionary: SQLiteP6RoleDictionaryRepository
    resources: SQLiteP6ResourceRepository
    expenses: SQLiteP6ExpenseRepository
    expense_service: P6ExpenseApplicationService
    cost_accounts: SQLiteP6CostAccountRepository
    cost_account_service: P6CostAccountApplicationService
    financial_periods: SQLiteP6FinancialPeriodRepository
    financial_period_service: P6FinancialPeriodApplicationService
    issues: SQLiteP6IssueRepository
    documents: SQLiteDocumentStore
    budget: SQLiteBudgetStore
    transaction_manager: SQLiteTransactionManager

    @classmethod
    def create(cls, connection: sqlite3.Connection) -> "PreviewRepositories":
        transaction_manager = SQLiteTransactionManager(connection)
        activities = SQLiteActivityMasterRepository(connection)
        wbs = SQLiteWBSMasterRepository(connection)
        relationships = SQLiteRelationshipMasterRepository(connection)
        constraints = SQLiteConstraintMasterRepository(connection)
        calendars = SQLiteCalendarMasterRepository(connection)
        calendar_assignments = SQLiteCalendarAssignmentRepository(connection)
        calendar_snapshots = SQLiteCalendarSnapshotRepository(connection)
        calendar_exceptions = SQLiteCalendarExceptionRepository(connection)
        calendar_work_hours = SQLiteCalendarWorkHourRepository(connection)
        resource_assignments = SQLiteP6ResourceAssignmentRepository(connection)
        resource_periods = SQLiteP6ResourceAssignmentPeriodRepository(connection)
        resource_assignment_service = P6ResourceAssignmentApplicationService(
            resource_assignments, transaction_manager
        )
        resource_period_service = P6ResourceAssignmentPeriodApplicationService(
            resource_periods, transaction_manager
        )
        resource_spread_service = P6ResourceSpreadApplicationService(
            SQLiteP6ResourceSpreadRepository(connection), transaction_manager
        )
        capacities = SQLiteP6ResourceCapacityRepository(connection)
        capacity_service = P6ResourceCapacityApplicationService(
            capacities, transaction_manager
        )
        rates = SQLiteP6ResourceRateRepository(connection)
        rate_service = P6ResourceRateApplicationService(rates, transaction_manager)
        settings = SQLiteProjectScheduleSettingsRepository(connection)
        fields = SQLiteP6FieldRegistryRepository(connection)
        field_service = P6FieldRegistryApplicationService(fields, transaction_manager)
        formula_definitions = SQLiteP6FormulaDefinitionRepository(connection)
        formula_definition_service = P6FormulaDefinitionApplicationService(
            formula_definitions, transaction_manager
        )
        formula_column_service = P6FormulaColumnService(
            field_service, formula_definition_service
        )
        udfs = SQLiteP6UserDefinedFieldRepository(connection)
        udf_service = P6UserDefinedFieldApplicationService(udfs, transaction_manager)
        mappings = SQLiteP6MappingRegistryRepository(connection)
        mapping_service = P6MappingRegistryApplicationService(
            mappings, transaction_manager
        )
        layouts = SQLiteP6LayoutRepository(connection)
        snapshots = SQLiteScheduleInputSnapshotRepository(connection)
        contexts = SQLiteCalculationContextRepository(connection)
        baselines = SQLiteP6BaselineRepository(connection)
        baseline_activities = SQLiteP6BaselineActivityRepository(connection)
        baseline_assignments = SQLiteP6BaselineRoleAssignmentRepository(connection)
        current_activity_values = SQLiteP6CurrentActivityRepository(connection)
        current_activity_service = P6CurrentActivityApplicationService(
            current_activity_values, transaction_manager
        )
        roles = SQLiteP6RoleRepository(connection)
        role_dictionary = SQLiteP6RoleDictionaryRepository(connection)
        resources = SQLiteP6ResourceRepository(connection)
        expenses = SQLiteP6ExpenseRepository(connection)
        expense_service = P6ExpenseApplicationService(expenses, transaction_manager)
        cost_accounts = SQLiteP6CostAccountRepository(connection)
        cost_account_service = P6CostAccountApplicationService(
            cost_accounts, transaction_manager
        )
        financial_periods = SQLiteP6FinancialPeriodRepository(connection)
        financial_period_service = P6FinancialPeriodApplicationService(
            financial_periods, transaction_manager
        )
        issues = SQLiteP6IssueRepository(connection)
        documents = SQLiteDocumentStore(connection)
        documents.initialize()
        budget = SQLiteBudgetStore(connection)
        budget.initialize()
        return cls(
            activities=activities,
            wbs=wbs,
            relationships=relationships,
            constraints=constraints,
            calendars=calendars,
            calendar_assignments=calendar_assignments,
            calendar_snapshots=calendar_snapshots,
            calendar_exceptions=calendar_exceptions,
            calendar_work_hours=calendar_work_hours,
            resource_assignments=resource_assignments,
            resource_periods=resource_periods,
            resource_assignment_service=resource_assignment_service,
            resource_period_service=resource_period_service,
            resource_spread_service=resource_spread_service,
            capacities=capacities,
            capacity_service=capacity_service,
            rates=rates,
            rate_service=rate_service,
            settings=settings,
            fields=fields,
            field_service=field_service,
            formula_definitions=formula_definitions,
            formula_definition_service=formula_definition_service,
            formula_column_service=formula_column_service,
            udfs=udfs,
            udf_service=udf_service,
            mappings=mappings,
            mapping_service=mapping_service,
            layouts=layouts,
            snapshots=snapshots,
            contexts=contexts,
            baselines=baselines,
            baseline_activities=baseline_activities,
            baseline_assignments=baseline_assignments,
            current_activity_values=current_activity_values,
            current_activity_service=current_activity_service,
            roles=roles,
            role_dictionary=role_dictionary,
            resources=resources,
            expenses=expenses,
            expense_service=expense_service,
            cost_accounts=cost_accounts,
            cost_account_service=cost_account_service,
            financial_periods=financial_periods,
            financial_period_service=financial_period_service,
            issues=issues,
            documents=documents,
            budget=budget,
            transaction_manager=transaction_manager,
        )


def _project_calendar_id(project_id: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", project_id).strip("-").upper() or "PROJECT"
    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:8].upper()
    return f"CUBI-{slug[:24]}-{digest}-CAL"


def _presentation_columns() -> tuple[LayoutColumn, ...]:
    return tuple(
        LayoutColumn(
            field_id=column.field_id,
            visible=column.visible,
            order=index,
            label=column.label,
            width=column.width,
            alignment=column.alignment,
            pinned=False,
            frozen=False,
        )
        for index, column in enumerate(LAYOUT_COLUMNS)
    )


def seed_presentation(repositories: PreviewRepositories, scope: BackendScope) -> None:
    """Seed the curated field catalogue and the initial persisted layout."""

    for field_id in CURATED_FIELD_IDS:
        repositories.field_service.save_field(
            PersistedP6Field(scope, REGISTRY_VERSION, get_field(field_id))
        )
    repositories.layouts.upsert(
        PersistedP6Layout(
            scope=scope,
            layout_scope=LAYOUT_SCOPE,
            view_id=LAYOUT_VIEW,
            revision=1,
            columns=_presentation_columns(),
            metadata={
                "source": "cubi-local-preview",
                "seed_version": PREVIEW_SEED_VERSION,
                "layoutName": "Classic Schedule Layout",
            },
        )
    )


PREVIEW_INTERCHANGE_FORMAT = P6MappingFormat.PRIMAVERA_XML


def _interchange_mappings(scope: BackendScope) -> tuple[PersistedP6Mapping, ...]:
    definitions = (
        ("PREVIEW-P6XML-ACTIVITY-ID", "Id", "activity.id"),
        ("PREVIEW-P6XML-ACTIVITY-NAME", "Name", "activity.name"),
    )
    return tuple(
        PersistedP6Mapping(
            scope=scope,
            definition=P6MappingDefinition(
                mapping_id=mapping_id,
                registry_version=REGISTRY_VERSION,
                format=PREVIEW_INTERCHANGE_FORMAT,
                subject_area="activity",
                source_field=source_field,
                canonical_field=canonical_field,
                status=P6MappingStatus.SUPPORTED,
            ),
        )
        for mapping_id, source_field, canonical_field in definitions
    )


def seed_interchange_mappings(
    repositories: PreviewRepositories, scope: BackendScope
) -> None:
    """Seed the provider mapping registry used by the real interchange codec."""

    for mapping in _interchange_mappings(scope):
        repositories.mapping_service.save_mapping(mapping)


def seed_resource_capacities(
    repositories: PreviewRepositories,
    fixture: DemoProjectFixture,
    scope: BackendScope,
) -> None:
    """Seed explicit effective-dated ceilings through the real typed repository.

    The values come from the fixture, not from assignment demand or a calendar
    default, and each segment gets its content-addressed identity.
    """

    for capacity in fixture.capacities:
        segment = ResourceMaxUnitsTime.create(
            resource_id=capacity.resource_id,
            max_units=capacity.max_units,
            unit_basis=capacity.unit_basis,
            hours_per_time_period=capacity.hours_per_time_period,
            effective_from=capacity.effective_from,
            effective_to=capacity.effective_to,
            source=capacity.source,
        )
        repositories.capacity_service.save(
            P6ResourceCapacityRecord(scope=scope, segment=segment)
        )


def seed_resource_rates(
    repositories: PreviewRepositories,
    fixture: DemoProjectFixture,
    scope: BackendScope,
) -> None:
    """Seed explicit effective-dated price facts through the real repository.

    Prices come from the fixture, not from assignment costs or a default, and
    each interval receives its content-addressed identity.
    """

    for rate in fixture.rates:
        fact = ResourceRateFact.create(
            resource_id=rate.resource_id,
            rate=rate.rate,
            basis=rate.basis,
            currency=rate.currency,
            unit=rate.unit,
            effective_from=rate.effective_from,
            effective_to=rate.effective_to,
            source=rate.source,
        )
        repositories.rate_service.save(P6ResourceRateRecord(scope=scope, fact=fact))


def seed_resource_master(
    repositories: PreviewRepositories,
    fixture: DemoProjectFixture,
    scope: BackendScope,
) -> None:
    """Seed the resource identities that the capacity/rate facts reference.

    Only the resources already named by the fixture are created; no synthetic
    resource is invented to fill the register.
    """

    for resource in fixture.resources:
        repositories.resources.save(
            P6Resource(
                scope.tenant_id,
                scope.project_id,
                scope.project_revision,
                resource.resource_id,
                resource.name,
                resource.resource_type,
                resource.parent_resource_id,
                resource.calendar_id,
                resource.default_units_per_time,
                resource.unit_of_measure,
                None,
                True,
            )
        )


def seed_wbs_nodes(
    repositories: PreviewRepositories,
    fixture: DemoProjectFixture,
    scope: BackendScope,
) -> dict[str, str]:
    """Persist the fixture WBS tree, then resolve every activity assignment.

    Nodes come from the explicit fixture, never from activity rows. The
    assignment map is a seed-time join; the runtime read path uses the persisted
    ``activity_wbs_assignment`` rows instead.
    """

    display_by_node: dict[str, str] = {}
    ordered = sorted(
        fixture.wbs_nodes,
        key=lambda node: 0 if node.parent_wbs_id is None else 1,
    )
    for node in ordered:
        stored = repositories.wbs.save(
            WBSMaster(
                scope=scope,
                wbs_id=node.wbs_id,
                parent_kind=(
                    WBSParentKind.PROJECT
                    if node.parent_wbs_id is None
                    else WBSParentKind.WBS
                ),
                parent_wbs_id=node.parent_wbs_id,
                code=node.local_code,
                name=node.name,
                sequence_number=node.sequence_number,
            )
        )
        display_by_node[f"{stored.code} {stored.name}"] = stored.wbs_id

    assignments: dict[str, str] = {}
    for activity_id, display in fixture.wbs.items():
        wbs_id = display_by_node.get(display)
        if wbs_id is None:
            raise PreviewRuntimeError(
                "PREVIEW_FIXTURE_WBS_REFERENCE_INVALID",
                f"Activity {activity_id} references unknown WBS node {display!r}.",
            )
        assignments[activity_id] = wbs_id
    return assignments


def project_root_wbs_id(project_id: str) -> str:
    return f"WBS-{project_id}"


def seed_project_root_wbs(
    repositories: PreviewRepositories,
    *,
    scope: BackendScope,
    name: str,
) -> None:
    """Create the single project-parent WBS node for a new project."""

    repositories.wbs.save(
        WBSMaster(
            scope=scope,
            wbs_id=project_root_wbs_id(scope.project_id),
            parent_kind=WBSParentKind.PROJECT,
            parent_wbs_id=None,
            code="1",
            name=name,
            sequence_number=0,
        )
    )


def seed_default_calendar(
    repositories: PreviewRepositories,
    *,
    scope: BackendScope,
    calendar_id: str,
    name: str,
    working_weekdays: frozenset[int],
    system: CalendarSystem,
    holidays: tuple[date, ...] = (),
) -> CalendarMaster:
    calendar = repositories.calendars.save(
        CalendarMaster(
            scope=scope,
            calendar_id=calendar_id,
            calendar_version=DEFAULT_CALENDAR_VERSION,
            kind="working-day",
            name=name,
            calendar_type="project",
        ),
        expected_revision=0,
    )
    repositories.calendar_snapshots.save(
        calendar,
        WorkingCalendar(
            working_weekdays=working_weekdays,
            holidays=frozenset(holidays),
            system=system,
        ),
    )
    return calendar


def seed_working_time_calendar(
    repositories: PreviewRepositories,
    *,
    scope: BackendScope,
    calendar_id: str,
    name: str,
    working_weekdays: frozenset[int],
    system: CalendarSystem,
    holidays: tuple[date, ...] = (),
) -> CalendarMaster:
    """Seed a split-shift calendar so the window has a real working-time target.

    The intervals are an explicit demo definition (morning and afternoon
    shifts), not a computed value, and the calendar is independent of the
    project calendar used by the schedule.
    """
    calendar = repositories.calendars.save(
        CalendarMaster(
            scope=scope,
            calendar_id=calendar_id,
            calendar_version=DEFAULT_CALENDAR_VERSION,
            kind="working-time",
            name=name,
            calendar_type="project",
        ),
        expected_revision=0,
    )
    repositories.calendar_snapshots.save(
        calendar,
        WorkingTimeCalendar(
            working_weekdays=working_weekdays,
            holidays=frozenset(holidays),
            daily_intervals={
                weekday: ((time(8, 0), time(12, 0)), (time(13, 0), time(17, 0)))
                for weekday in working_weekdays
            },
            system=system,
        ),
    )
    return calendar


class PreviewProjectInitializer:
    """Initialise a newly-created project with real structured metadata."""

    def __init__(self, repositories: PreviewRepositories) -> None:
        self.repositories = repositories

    def __call__(self, scope: BackendScope, name: str) -> None:
        seed_project_root_wbs(self.repositories, scope=scope, name=name)
        seed_presentation(self.repositories, scope)
        seed_interchange_mappings(self.repositories, scope)
        seed_default_calendar(
            self.repositories,
            scope=scope,
            calendar_id=_project_calendar_id(scope.project_id),
            name=PREVIEW_DEFAULT_CALENDAR_NAME,
            working_weekdays=PREVIEW_DEFAULT_WORKING_WEEKDAYS,
            system=CalendarSystem.GREGORIAN,
        )


def _to_activity(scope: BackendScope, item, wbs_id: str) -> ActivityMaster:
    return ActivityMaster(
        scope=scope,
        activity_id=item.activity_id,
        duration_value=Decimal(item.duration),
        duration_unit=DurationUnit.WORKING_DAY,
        actual_start=item.actual_start,
        actual_finish=item.actual_finish,
        remaining_duration=item.remaining_duration,
        percent_complete=item.percent_complete,
        planned_finish=None,
        leveling_priority=item.leveling_priority,
        original_duration=item.duration,
        name=item.name,
        short_name=item.short_name,
        activity_type=item.activity_type,
        status=item.status,
        status_code=item.status_code,
        wbs_id=wbs_id,
    )


def _to_relationship(scope: BackendScope, item) -> RelationshipMaster:
    return RelationshipMaster(
        scope=scope,
        relationship_id=item.relationship_id,
        predecessor_id=item.predecessor_id,
        successor_id=item.successor_id,
        relationship_type=item.relationship_type,
        lag_value=Decimal(item.lag),
        lag_unit=DurationUnit.WORKING_DAY,
    )


def publish_fixture_snapshot(
    repositories: PreviewRepositories,
    fixture: DemoProjectFixture,
    scope: BackendScope,
) -> None:
    publisher = AuthoritativeScheduleSnapshotPublisher(
        composer=AuthoritativeScheduleInputComposer(
            activity_repository=repositories.activities,
            relationship_repository=repositories.relationships,
            constraint_repository=repositories.constraints,
            calendar_repository=repositories.calendars,
            calendar_assignment_repository=repositories.calendar_assignments,
            calendar_snapshot_repository=repositories.calendar_snapshots,
            resource_assignment_repository=repositories.resource_assignments,
            resource_period_repository=repositories.resource_periods,
            project_schedule_settings_repository=repositories.settings,
            wbs_repository=repositories.wbs,
        ),
        snapshot_repository=repositories.snapshots,
        calculation_context_repository=repositories.contexts,
        transaction_manager=repositories.transaction_manager,
        rules_version=PREVIEW_RULES_VERSION,
        engine_version=PREVIEW_ENGINE_VERSION,
        clock=lambda: fixture.snapshot_clock,
        snapshot_id_factory=lambda: fixture.snapshot_id,
    )
    publisher.publish(
        scope,
        timezone_name=fixture.timezone_name,
        actor_id="preview-seed",
        request_id=f"preview-seed:{fixture.project_id}",
    )


def seed_demo_project(
    repositories: PreviewRepositories,
    store: PreviewStore,
    fixture: DemoProjectFixture,
) -> None:
    scope = BackendScope(PREVIEW_TENANT_ID, fixture.project_id, fixture.revision)
    seed_presentation(repositories, scope)
    seed_interchange_mappings(repositories, scope)
    seed_resource_capacities(repositories, fixture, scope)
    seed_resource_rates(repositories, fixture, scope)
    seed_resource_master(repositories, fixture, scope)
    calendar = seed_default_calendar(
        repositories,
        scope=scope,
        calendar_id=fixture.calendar_id,
        name=fixture.calendar_name,
        working_weekdays=fixture.working_weekdays,
        system=fixture.calendar_system,
        holidays=fixture.holiday_dates,
    )
    snapshot = repositories.calendar_snapshots.get(calendar)
    if snapshot is None:
        raise PreviewRuntimeError("PREVIEW_FIXTURE_CALENDAR_SNAPSHOT_MISSING")
    if "system" not in snapshot.snapshot:
        raise PreviewRuntimeError("PREVIEW_FIXTURE_CALENDAR_SYSTEM_MISSING")
    seed_working_time_calendar(
        repositories,
        scope=scope,
        calendar_id=f"{fixture.calendar_id}-TIME",
        name=f"{fixture.calendar_name} split shifts",
        working_weekdays=fixture.working_weekdays,
        system=fixture.calendar_system,
        holidays=fixture.holiday_dates,
    )

    settings = ProjectScheduleSettings(
        scope=scope,
        mode=_date_based_mode(),
        project_calendar=CalendarReference(
            calendar.calendar_id,
            calendar.calendar_version,
            calendar.kind,
            fixture.calendar_system,
        ),
        project_start=fixture.project_start,
        project_finish=None,
        schedule_options=ScheduleOptions(data_date=fixture.data_date),
        project_leveling_priority=DEFAULT_PROJECT_LEVELING_PRIORITY,
    )
    repositories.settings.save(settings, expected_revision=0)

    wbs_by_activity = seed_wbs_nodes(repositories, fixture, scope)
    for item in fixture.activities:
        repositories.activities.save(
            _to_activity(scope, item, wbs_by_activity[item.activity_id])
        )
    for item in fixture.relationships:
        repositories.relationships.save(_to_relationship(scope, item))
    publish_fixture_snapshot(repositories, fixture, scope)

    store.insert_project(
        tenant_id=PREVIEW_TENANT_ID,
        project_id=fixture.project_id,
        name=fixture.name,
        revision=fixture.revision,
        wbs_by_activity=dict(fixture.wbs),
        demo=True,
        created_at=fixture.snapshot_clock,
        start_date=fixture.project_start.isoformat(),
        date_system=fixture.calendar_system.value,
        primary_calendar_id=fixture.calendar_id,
    )
    store.add_members(PREVIEW_TENANT_ID, fixture.project_id, DEMO_PROJECT_MEMBER_USER_IDS)


def _date_based_mode():
    from construction_pm.scheduling.authoritative_schedule import (
        AuthoritativeScheduleMode,
    )

    return AuthoritativeScheduleMode.DATE_BASED


def seed_database(connection: sqlite3.Connection) -> None:
    """Seed a new guarded preview database. Called only by storage.open_*."""

    repositories = PreviewRepositories.create(connection)
    store = PreviewStore(connection)
    form_repository = SQLiteFormBuilderRepository(connection)
    form_binding_provider = PreviewFormBindingProvider(
        store,
        repositories.activities,
        repositories.wbs,
        repositories.resource_assignments,
    )
    form_builder_api = FormBuilderAPI(
        form_repository,
        default_project_policy(),
        binding_provider=form_binding_provider,
        clock=PreviewClock().now,
    )
    seed_organization_library(form_repository, PREVIEW_TENANT_ID, "preview-admin")
    for fixture in DEMO_PROJECTS:
        seed_demo_project(repositories, store, fixture)
    connection.commit()


def build_calendar_registry(connection: sqlite3.Connection) -> CalendarResolverRegistry:
    """Read every persisted calendar definition into one fail-closed registry.

    Calendar exceptions become local exception layers and persisted work-hour
    rules are applied to the stored snapshot, so a workweek edit changes the
    resolver the schedule actually uses. Working-day and working-time calendars
    are both registered; base-calendar references are bound after every calendar
    has been read so the order of rows cannot matter. Ambiguous or unsupported
    rules still fail closed instead of being ignored.
    """

    exception_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        ("calendar_exception",),
    ).fetchone()
    exception_repository = (
        SQLiteCalendarExceptionRepository(connection)
        if exception_table is not None
        else None
    )
    work_hour_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        ("calendar_work_hour_rule",),
    ).fetchone()
    work_hour_repository = (
        SQLiteCalendarWorkHourRepository(connection)
        if work_hour_table is not None
        else None
    )

    scopes = connection.execute(
        "SELECT DISTINCT tenant_id, project_id, project_revision FROM calendar_master "
        "ORDER BY tenant_id, project_id, project_revision"
    ).fetchall()
    master_repository = SQLiteCalendarMasterRepository(connection)
    snapshot_repository = SQLiteCalendarSnapshotRepository(connection)
    day_resolvers: dict[str, WorkingTimeResolver] = {}
    time_resolvers: dict[str, TimeAwareWorkingTimeResolver] = {}
    canonical_by_key: dict[str, dict[str, object]] = {}
    exception_layers: dict[str, CalendarExceptionLayers] = {}
    exception_signature_by_key: dict[str, tuple[dict[str, object], ...]] = {}
    base_references: dict[str, CalendarReference] = {}
    pending_bases: list[tuple[str, str, str, str]] = []

    for tenant_id, project_id, revision in scopes:
        scope = BackendScope(str(tenant_id), str(project_id), int(revision))
        for calendar in master_repository.list(scope):
            if calendar.kind not in {"working-day", "working-time"}:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_KIND_UNSUPPORTED",
                    f"Unsupported calendar kind {calendar.kind} for "
                    f"{calendar.calendar_id}@{calendar.calendar_version}.",
                )
            record = snapshot_repository.get(calendar)
            if record is None:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_SNAPSHOT_MISSING",
                    f"No immutable snapshot exists for {calendar.calendar_id}@"
                    f"{calendar.calendar_version}.",
                )
            try:
                definition = (
                    WorkingTimeCalendar.from_canonical_snapshot(record.snapshot)
                    if calendar.kind == "working-time"
                    else WorkingCalendar.from_canonical_snapshot(record.snapshot)
                )
            except (TypeError, ValueError) as exc:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_SNAPSHOT_INVALID",
                    f"Calendar snapshot for {calendar.calendar_id}@"
                    f"{calendar.calendar_version} is invalid.",
                ) from exc
            if work_hour_repository is not None:
                rules = {
                    kind: tuple(
                        work_hour_repository.list(
                            scope, calendar.calendar_id, calendar.calendar_version, kind
                        )
                    )
                    for kind in (
                        "standard_work_week",
                        "standard_detailed_work_hours",
                        "detailed_work_hours",
                        "total_work_hours",
                    )
                }
                try:
                    definition, _ = apply_weekly_work_hour_rules(definition, rules)
                except ValueError as exc:
                    raise PreviewRuntimeError(
                        "PREVIEW_CALENDAR_WORK_HOURS_INVALID",
                        f"Calendar work hours for {calendar.calendar_id}@"
                        f"{calendar.calendar_version} cannot be applied: {exc}.",
                    ) from exc
            canonical = definition.canonical_snapshot()
            key = f"{calendar.calendar_id}@{calendar.calendar_version}"
            existing = canonical_by_key.get(key)
            if existing is not None and existing != canonical:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_CONFLICT",
                    f"Calendar key {key} resolves to different snapshots in two scopes.",
                )
            canonical_by_key[key] = canonical
            if calendar.kind == "working-time":
                time_resolvers[key] = TimeAwareWorkingTimeResolver(definition)
            else:
                day_resolvers[key] = WorkingTimeResolver(definition)
            if calendar.base_calendar_id is not None or calendar.base_calendar_version is not None:
                if not calendar.base_calendar_id or not calendar.base_calendar_version:
                    raise PreviewRuntimeError(
                        "PREVIEW_CALENDAR_INHERITANCE_INVALID",
                        f"Incomplete base reference on {key}.",
                    )
                pending_bases.append(
                    (key, calendar.base_calendar_id, calendar.base_calendar_version, definition.system.value)
                )

            if exception_repository is None:
                continue
            persisted = exception_repository.list(
                scope, calendar.calendar_id, calendar.calendar_version
            )
            if not persisted:
                continue
            try:
                local_exceptions = tuple(
                    persisted_exception_to_kernel(item) for item in persisted
                )
            except CalendarExceptionKernelError as exc:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_EXCEPTION_INVALID",
                    f"Calendar exception for {key} cannot be consumed: {exc}.",
                ) from exc
            signature = tuple(item.canonical_snapshot() for item in persisted)
            previous = exception_signature_by_key.get(key)
            if previous is not None and previous != signature:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_EXCEPTION_CONFLICT",
                    f"Calendar key {key} has different exception layers in two scopes.",
                )
            exception_signature_by_key[key] = signature
            exception_layers[key] = CalendarExceptionLayers(local=local_exceptions)

    kinds_by_key = {
        **{key: "working-time" for key in time_resolvers},
        **{key: "working-day" for key in day_resolvers},
    }
    for key, base_id, base_version, system in pending_bases:
        parent_key = f"{base_id}@{base_version}"
        if parent_key not in kinds_by_key:
            raise PreviewRuntimeError(
                "PREVIEW_CALENDAR_BASE_NOT_FOUND",
                f"Base calendar {parent_key} for {key} is not registered.",
            )
        base_references[key] = CalendarReference(
            base_id, base_version, kinds_by_key[parent_key], CalendarSystem(system)
        )

    return CalendarResolverRegistry(
        day_resolvers=day_resolvers,
        time_resolvers=time_resolvers,
        exception_layers=exception_layers,
        base_calendar_references=base_references,
    )


@dataclass(frozen=True)
class PreviewWorkspaceReadProvider:
    """Build the authorized workspace envelope from persisted preview state.

    ``wbs_repository`` switches the projection to the canonical WBS contract
    (v2). Without it the adapter keeps the legacy v1 display mapping that is
    still stored in preview project metadata.
    """

    activity_repository: object
    field_service: object
    layout_repository: object
    schedule_facts_provider: WorkspaceScheduleFactsProvider
    store: PreviewStore
    formula_column_service: object | None = None
    wbs_repository: object | None = None
    relationship_repository: object | None = None

    def read(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext | None = None,
    ) -> Mapping[str, object] | None:
        from construction_pm.p6_layout_definition_repository import (
            SQLiteP6LayoutRepository,
        )
        from construction_pm.p6_field_registry_repository import (
            P6FieldRegistryApplicationService,
        )

        if not isinstance(self.field_service, P6FieldRegistryApplicationService):
            raise PreviewRuntimeError("PREVIEW_FIELD_SERVICE_INVALID")
        if not isinstance(self.layout_repository, SQLiteP6LayoutRepository):
            raise PreviewRuntimeError("PREVIEW_LAYOUT_REPOSITORY_INVALID")
        if self.wbs_repository is not None:
            provider = PersistedWorkspaceReadProvider(
                activity_repository=self.activity_repository,  # type: ignore[arg-type]
                field_service=self.field_service,
                layout_repository=self.layout_repository,
                formula_column_service=self.formula_column_service,  # type: ignore[arg-type]
                schedule_facts_provider=self.schedule_facts_provider,
                wbs_repository=self.wbs_repository,  # type: ignore[arg-type]
                relationship_repository=self.relationship_repository,  # type: ignore[arg-type]
            )
            return provider.read(scope, auth_context=auth_context)
        provider = PersistedWorkspaceReadProvider(
            activity_repository=self.activity_repository,  # type: ignore[arg-type]
            field_service=self.field_service,
            layout_repository=self.layout_repository,
            formula_column_service=self.formula_column_service,  # type: ignore[arg-type]
            schedule_facts_provider=self.schedule_facts_provider,
            wbs_by_activity=self.store.wbs_for(scope.tenant_id, scope.project_id),
        )
        return provider.read(scope, auth_context=auth_context)


class PreviewAIPermissionAdapter:
    """Default-deny preview grant adapter bound to an active server-side session."""

    def __init__(self, sessions: object, store: PreviewStore) -> None:
        self.sessions = sessions
        self.store = store

    def allowed(self, proposal: AIActionProposal, *, subject_id: str | None = None) -> bool:
        if not isinstance(subject_id, str) or not subject_id.strip():
            return False
        active_session = getattr(self.sessions, "active_for_user", lambda _user: None)(subject_id)
        if (
            active_session is None
            or active_session.user_id != subject_id
            or active_session.tenant_id != proposal.tenant_id
        ):
            return False
        project = self.store.get_for_user(proposal.tenant_id, proposal.project_id, subject_id)
        if project is None or str(project.revision) != proposal.project_revision_id:
            return False
        if proposal.action != "create" or not proposal.requires_human_approval:
            return False
        if proposal.tool_name == "activity.create":
            return proposal.resource_domain == "activities" and bool(
                {"planner", "project_admin"} & set(active_session.roles)
            )
        if proposal.tool_name == "project.plan.create":
            return proposal.resource_domain == "projects" and "project_admin" in active_session.roles
        return False


@dataclass
class PreviewRuntime:
    database: Path
    web_root: Path | None
    connection: sqlite3.Connection
    store: PreviewStore
    sessions: PreviewSessionRepository
    lifecycle_api: ProjectLifecycleAPI
    policy: RoleBasedAuthorizationPolicy
    app: ProjectLifecycleWsgiApp
    clock: PreviewClock
    ai_assistant_enabled: bool = False
    ai_actions_enabled: bool = False
    ai_tool_names: tuple[str, ...] = ()

    def close(self) -> None:
        self.connection.close()

    def health(self) -> dict[str, object]:
        projects = self.store.project_rows()
        activity_count = self.connection.execute(
            "SELECT COUNT(*) FROM activity_master WHERE tenant_id=?",
            (PREVIEW_TENANT_ID,),
        ).fetchone()
        capacity_count = self.connection.execute(
            "SELECT COUNT(*) FROM p6_resource_capacity_segment WHERE tenant_id=?",
            (PREVIEW_TENANT_ID,),
        ).fetchone()
        rate_count = self.connection.execute(
            "SELECT COUNT(*) FROM p6_resource_rate_fact WHERE tenant_id=?",
            (PREVIEW_TENANT_ID,),
        ).fetchone()
        resource_count = self.connection.execute(
            "SELECT COUNT(*) FROM p6_resource_master WHERE tenant_id=?",
            (PREVIEW_TENANT_ID,),
        ).fetchone()
        wbs_count = self.connection.execute(
            "SELECT COUNT(*) FROM wbs_master WHERE tenant_id=?",
            (PREVIEW_TENANT_ID,),
        ).fetchone()
        return {
            "status": "ok",
            "mode": "local-full-stack-preview",
            "seed_version": PREVIEW_SEED_VERSION,
            "tenant_id": PREVIEW_TENANT_ID,
            "project_count": len(projects),
            "demo_project_count": sum(1 for item in projects if item["demo"]),
            "activity_count": int(activity_count[0]) if activity_count else 0,
            "wbs_node_count": int(wbs_count[0]) if wbs_count else 0,
            "capacity_segment_count": int(capacity_count[0]) if capacity_count else 0,
            "rate_fact_count": int(rate_count[0]) if rate_count else 0,
            "resource_count": int(resource_count[0]) if resource_count else 0,
            "session_count": self.sessions.count(),
            "assistant": {
                "enabled": self.ai_assistant_enabled,
                "actions_enabled": self.ai_actions_enabled,
                "provider_configured": self.ai_assistant_enabled,
                "provider_environment_complete": all(
                    os.environ.get(key, "").strip()
                    for key in ("CUBI_AI_API_KEY", "CUBI_AI_BASE_URL", "CUBI_AI_MODEL")
                ),
                "available_tools": list(self.ai_tool_names),
            },
            "private_owner_login_enabled": bool(
                os.environ.get("CUBI_PREVIEW_PRIVATE_ACCESS_TOKEN", "").strip()
            ),
        }

    def projects_for_user(self, user_id: str) -> tuple[ProjectSummary, ...]:
        return self.store.list_for_user(PREVIEW_TENANT_ID, user_id)


def open_preview_runtime(
    database: Path,
    *,
    web_root: Path | None = None,
    reset: bool = False,
) -> PreviewRuntime:
    database = Path(database).expanduser().resolve()
    try:
        connection = open_preview_database(
            database,
            seed=seed_database,
            reset=reset,
        )
    except PreviewDatabaseError as exc:
        raise PreviewRuntimeError(exc.code, str(exc)) from exc

    repositories = PreviewRepositories.create(connection)
    store = PreviewStore(connection)
    form_repository = SQLiteFormBuilderRepository(connection)
    form_binding_provider = PreviewFormBindingProvider(
        store,
        repositories.activities,
        repositories.wbs,
        repositories.resource_assignments,
    )
    form_builder_api = FormBuilderAPI(
        form_repository,
        default_project_policy(),
        binding_provider=form_binding_provider,
        directory_provider=PreviewFormDirectory(store),
        clock=PreviewClock().now,
    )
    seed_organization_library(form_repository, PREVIEW_TENANT_ID, "preview-admin")
    sessions = PreviewSessionRepository()
    policy = default_project_policy()
    public_demo = os.environ.get("CUBI_PREVIEW_PUBLIC_DEMO", "").strip().lower() in {
        "1", "true", "yes",
    }
    project_repository = PreviewProjectRepository(
        store,
        initializer=PreviewProjectInitializer(repositories),
        # On the hosted public demo, newly-created projects belong only to their
        # creator. The seeded fixture projects remain shared and read-only.
        member_user_ids=() if public_demo else DEMO_PROJECT_MEMBER_USER_IDS,
    )
    lifecycle_service = ProjectLifecycleService(sessions, project_repository, policy)
    lifecycle_api = ProjectLifecycleAPI(lifecycle_service)

    query_provider = AuthoritativeScheduleQueryProvider(
        snapshot_repository=repositories.snapshots,
        calendar_registry_factory=lambda: build_calendar_registry(connection),
        calculation_context_repository=repositories.contexts,
    )
    facts_provider = PublishedScheduleFactsProvider(repositories.snapshots, query_provider)
    legacy_workspace_provider = PreviewWorkspaceReadProvider(
        activity_repository=repositories.activities,
        field_service=repositories.field_service,
        layout_repository=repositories.layouts,
        formula_column_service=repositories.formula_column_service,
        schedule_facts_provider=facts_provider,
        store=store,
    )
    workspace_service = WorkspaceControlRoomReadService(
        legacy_workspace_provider, policy
    )
    canonical_workspace_provider = PreviewWorkspaceReadProvider(
        activity_repository=repositories.activities,
        field_service=repositories.field_service,
        layout_repository=repositories.layouts,
        formula_column_service=repositories.formula_column_service,
        schedule_facts_provider=facts_provider,
        store=store,
        wbs_repository=repositories.wbs,
        relationship_repository=repositories.relationships,
    )
    workspace_v2_service = WorkspaceControlRoomReadService(
        canonical_workspace_provider, policy
    )
    backend_api = BackendP0API(
        BackendP0ApplicationService(
            repository=InMemoryBackendP0Repository(),
            transaction_manager=repositories.transaction_manager,
            authorization_policy=policy,
        ),
        workspace_read_service=workspace_service,
    )

    publisher = AuthoritativeScheduleSnapshotPublisher(
        composer=AuthoritativeScheduleInputComposer(
            activity_repository=repositories.activities,
            relationship_repository=repositories.relationships,
            constraint_repository=repositories.constraints,
            calendar_repository=repositories.calendars,
            calendar_assignment_repository=repositories.calendar_assignments,
            calendar_snapshot_repository=repositories.calendar_snapshots,
            resource_assignment_repository=repositories.resource_assignments,
            resource_period_repository=repositories.resource_periods,
            project_schedule_settings_repository=repositories.settings,
            wbs_repository=repositories.wbs,
        ),
        snapshot_repository=repositories.snapshots,
        calculation_context_repository=repositories.contexts,
        transaction_manager=repositories.transaction_manager,
        rules_version=PREVIEW_RULES_VERSION,
        engine_version=PREVIEW_ENGINE_VERSION,
    )
    snapshot_api = P6ScheduleSnapshotPublicationAPI(
        publisher,
        policy,
        repositories.settings,
        repositories.calendars,
    )
    baseline_api = P6BaselineAPI(
        P6BaselineApplicationService(
            repositories.baselines, repositories.transaction_manager
        ),
        policy,
    )
    baseline_update_service = P6BaselineUpdateService(
        repository=repositories.baseline_activities,
        transaction_manager=repositories.transaction_manager,
        baseline_repository=repositories.baselines,
        current_source=repositories.current_activity_service,
    )
    baseline_update_api = P6BaselineUpdateAPI(
        baseline_update_service, policy
    )
    baseline_assignment_api = P6BaselineAssignmentAPI(
        P6BaselineAssignmentService(
            repository=repositories.baseline_assignments,
            baseline_repository=repositories.baselines,
            baseline_activity_repository=repositories.baseline_activities,
            transaction_manager=repositories.transaction_manager,
        ),
        policy,
    )
    baseline_conversion_api = P6BaselineConversionAPI(
        P6BaselineConversionService(
            baseline_repository=repositories.baselines,
            baseline_activity_repository=repositories.baseline_activities,
            current_source=repositories.current_activity_service,
            transaction_manager=repositories.transaction_manager,
        ),
        policy,
    )

    def _evm_resolver(scope: BackendScope) -> WorkingTimeResolver:
        """Resolve the persisted project calendar for this EVM measurement."""
        settings = repositories.settings.get(scope)
        if settings is None:
            raise P6EarnedValueReadModelError("EVM_PROJECT_CALENDAR_REQUIRED")
        try:
            registry = build_calendar_registry(connection)
            return registry.resolve(settings.project_calendar)
        except PreviewRuntimeError as exc:
            raise P6EarnedValueReadModelError(exc.code) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise P6EarnedValueReadModelError(
                "EVM_PROJECT_CALENDAR_UNRESOLVED"
            ) from exc

    earned_value_read_api = P6EarnedValueReadModelAPI(
        P6EarnedValueReadModelService(
            baseline_activities=repositories.baseline_activities,
            activities=repositories.activities,
            actuals=SQLiteP6ActivityPeriodActualRepository(connection),
            expenses=repositories.expenses,
            resolver_provider=_evm_resolver,
            wbs_repository=repositories.wbs,
            resource_assignments=repositories.resource_assignments,
        ),
        policy,
    )

    ai_assistant_enabled = os.environ.get("CUBI_AI_ENABLED", "").strip().lower() in {
        "1", "true", "yes",
    }
    # The proposal/approve/execute surface is deterministic and does not need a
    # chat provider. It can therefore be enabled on its own for managed preview
    # and CI without inventing provider credentials; the conversational endpoint
    # still fails closed unless CUBI_AI_ENABLED composes a real provider.
    ai_actions_enabled = ai_assistant_enabled or os.environ.get(
        "CUBI_AI_ACTIONS_ENABLED", ""
    ).strip().lower() in {"1", "true", "yes"}
    ai_assistant_provider = None
    ai_action_runtime = None
    ai_tool_names: tuple[str, ...] = ()
    if ai_assistant_enabled:
        # Provider credentials are only read from the server environment. Missing
        # or invalid configuration fails closed; there is no fake provider.
        ai_assistant_provider = OpenAICompatibleChatProvider.from_environment()
    if ai_actions_enabled:
        action_store = SQLiteAIActionRuntimeStore(connection)
        idempotency_store = SQLiteAIActionExecutionIdempotencyStore(connection)
        permission_adapter = PreviewAIPermissionAdapter(sessions, store)
        activity_api = P6ActivityMasterAPI(repositories.activities, policy)
        relationship_api = P6RelationshipAPI(
            repositories.relationships, policy, repositories.activities,
        )
        activity_tool = build_activity_create_tool(
            activity_api=activity_api,
            idempotency_store=idempotency_store,
            transaction_manager=repositories.transaction_manager,
        )
        project_plan_tool = build_project_plan_create_tool(
            lifecycle_api=lifecycle_api,
            get_active_session_for_user=sessions.active_for_user,
            project_store=store,
            repositories=repositories,
            activity_api=activity_api,
            relationship_api=relationship_api,
            schedule_snapshot_api=snapshot_api,
            backend_api=backend_api,
            idempotency_store=idempotency_store,
            authorization_policy=policy,
            timezone_name="Asia/Tehran",
        )
        ai_action_runtime = AIActionRuntime(
            store=action_store,
            permission_adapter=permission_adapter,
            audit_sink=action_store,
            tools=(activity_tool, project_plan_tool),
            clock=lambda: datetime.now(timezone.utc),
            transaction_manager=repositories.transaction_manager,
        )
        ai_tool_names = ("activity.create", "project.plan.create")

    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=lifecycle_api,
        snapshot_repository=repositories.snapshots,
        calendar_registry_factory=lambda: build_calendar_registry(connection),
        calculation_context_repository=repositories.contexts,
        authorization_policy=policy,
        activity_master_repository=repositories.activities,
        wbs_master_repository=repositories.wbs,
        workspace_read_v2_service=workspace_v2_service,
        relationship_master_repository=repositories.relationships,
        schedule_snapshot_publication_api=snapshot_api,
        backend_p0_api=backend_api,
        p6_field_registry_api=P6FieldRegistryAPI(
            repositories.field_service,
            repositories.udf_service,
            policy,
            repositories.formula_column_service,
        ),
        p6_layout_definition_api=P6LayoutDefinitionAPI(repositories.layouts, policy),
        p6_formula_authority_api=P6FormulaAuthorityAPI(
            repositories.field_service,
            policy,
            repositories.formula_column_service,
        ),
        p6_formula_column_api=P6FormulaColumnAPI(
            repositories.formula_column_service,
            policy,
        ),
        p6_calendar_read_api=P6CalendarReadAPI(
            repositories.calendars,
            repositories.calendar_snapshots,
            policy,
        ),
        p6_calendar_api=P6CalendarAPI(
            repositories.calendars,
            repositories.calendar_snapshots,
            repositories.calendar_exceptions,
            policy,
            work_hours_repository=repositories.calendar_work_hours,
            transaction_manager=repositories.transaction_manager,
        ),
        p6_baseline_api=baseline_api,
        p6_baseline_update_api=baseline_update_api,
        p6_baseline_assignment_api=baseline_assignment_api,
        p6_baseline_conversion_api=baseline_conversion_api,
        p6_earned_value_read_api=earned_value_read_api,
        p6_interchange_api=P6InterchangeAPI(
            mapping_service=repositories.mapping_service,
            authorization_policy=policy,
            codecs={PREVIEW_INTERCHANGE_FORMAT: P6PrimaveraXmlCodec()},
        ),
        p6_role_api=P6RoleAPI(repositories.roles, policy),
        p6_role_details_api=P6RoleDetailsAPI(
            repositories.roles,
            repositories.resources,
            repositories.role_dictionary,
            policy,
        ),
        p6_resource_api=P6ResourceAPI(
            repositories.resources,
            policy,
            repositories.calendars,
        ),
        p6_expense_api=P6ExpenseAPI(repositories.expense_service, policy),
        p6_cost_account_api=P6CostAccountAPI(repositories.cost_account_service, policy),
        p6_financial_period_api=P6FinancialPeriodAPI(
            repositories.financial_period_service, policy
        ),
        p6_issue_api=P6IssueAPI(repositories.issues, policy, repositories.transaction_manager),
        document_api=DocumentAPI(
            DocumentApplicationService(
                repositories.documents,
                policy,
                RolePermissionDocumentLifecycleAuthorizer(),
                repositories.transaction_manager,
            )
        ),
        budget_api=BudgetAPI(
            BudgetApplicationService(
                repositories.budget,
                policy,
                repositories.transaction_manager,
            )
        ),
        resource_read_api=P6ResourceReadAPI(
            repositories.resource_assignment_service,
            repositories.resource_period_service,
            repositories.resource_spread_service,
            policy,
        ),
        resource_write_api=P6ResourceWriteAPI(
            repositories.resource_period_service,
            policy,
            assignment_service=repositories.resource_assignment_service,
        ),
        # The assignment read API also feeds the persisted leveling resolver,
        # so the resolver receives the exact same calendar repositories the
        # schedule core already reads.
        resource_calendar_master_repository=repositories.calendars,
        resource_calendar_snapshot_repository=repositories.calendar_snapshots,
        resource_calendar_exception_repository=repositories.calendar_exceptions,
        resource_calendar_work_hours_repository=repositories.calendar_work_hours,
        p6_resource_capacity_read_api=P6ResourceCapacityReadAPI(
            repositories.capacity_service,
            policy,
        ),
        p6_resource_capacity_write_api=P6ResourceCapacityWriteAPI(
            repositories.capacity_service,
            policy,
            clock=PreviewClock(),
        ),
        p6_resource_rate_read_api=P6ResourceRateReadAPI(
            repositories.rate_service,
            policy,
        ),
        p6_resource_rate_write_api=P6ResourceRateWriteAPI(
            repositories.rate_service,
            policy,
            clock=PreviewClock(),
        ),
        clock=PreviewClock(),
        ai_action_runtime=ai_action_runtime,
        ai_assistant_provider=ai_assistant_provider,
        form_builder_api=form_builder_api,
    )
    return PreviewRuntime(
        database=database,
        web_root=None if web_root is None else Path(web_root).expanduser().resolve(),
        connection=connection,
        store=store,
        sessions=sessions,
        lifecycle_api=lifecycle_api,
        policy=policy,
        app=app,
        clock=PreviewClock(),
        ai_assistant_enabled=ai_assistant_enabled,
        ai_actions_enabled=ai_actions_enabled,
        ai_tool_names=ai_tool_names,
    )


__all__ = [
    "PREVIEW_ENGINE_VERSION",
    "PREVIEW_RULES_VERSION",
    "PreviewClock",
    "PreviewRepositories",
    "PreviewRuntime",
    "PreviewRuntimeError",
    "build_calendar_registry",
    "open_preview_runtime",
    "seed_database",
    "seed_resource_capacities",
    "seed_resource_rates",
]
