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
from datetime import date, datetime, timezone
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
from construction_pm.project_forms import FormBuilderAPI, SQLiteFormBuilderRepository
from construction_pm.ai_action_runtime import AIActionProposal, AIActionRuntime, SQLiteAIActionRuntimeStore
from construction_pm.ai_assistant_orchestration import build_ai_chat_provider_from_environment
from construction_pm.quantity_takeoff import (
    SQLiteQuantityTakeoffRepository,
    build_quantity_takeoff_create_tool,
)
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
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarAssignmentRepository,
    SQLiteCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import (
    SQLiteCalendarSnapshotRepository,
)
from construction_pm.constraint_master_repository import (
    SQLiteConstraintMasterRepository,
)
from construction_pm.http.production_composition import (
    build_project_lifecycle_wsgi_app,
)
from construction_pm.http.project_lifecycle_routes import Clock
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
    SQLiteP6FieldRegistryRepository,
)
from construction_pm.p6_formula_authority_api import P6FormulaAuthorityAPI
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
from construction_pm.p6_relationship_api import P6RelationshipAPI
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
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
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.time_duration import DurationUnit

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
    relationships: SQLiteRelationshipMasterRepository
    constraints: SQLiteConstraintMasterRepository
    calendars: SQLiteCalendarMasterRepository
    calendar_assignments: SQLiteCalendarAssignmentRepository
    calendar_snapshots: SQLiteCalendarSnapshotRepository
    resource_assignments: SQLiteP6ResourceAssignmentRepository
    resource_periods: SQLiteP6ResourceAssignmentPeriodRepository
    resource_spreads: SQLiteP6ResourceSpreadRepository
    capacities: SQLiteP6ResourceCapacityRepository
    capacity_service: P6ResourceCapacityApplicationService
    settings: SQLiteProjectScheduleSettingsRepository
    fields: SQLiteP6FieldRegistryRepository
    field_service: P6FieldRegistryApplicationService
    udfs: SQLiteP6UserDefinedFieldRepository
    udf_service: P6UserDefinedFieldApplicationService
    mappings: SQLiteP6MappingRegistryRepository
    mapping_service: P6MappingRegistryApplicationService
    layouts: SQLiteP6LayoutRepository
    snapshots: SQLiteScheduleInputSnapshotRepository
    contexts: SQLiteCalculationContextRepository
    transaction_manager: SQLiteTransactionManager

    @classmethod
    def create(cls, connection: sqlite3.Connection) -> "PreviewRepositories":
        transaction_manager = SQLiteTransactionManager(connection)
        activities = SQLiteActivityMasterRepository(connection)
        relationships = SQLiteRelationshipMasterRepository(connection)
        constraints = SQLiteConstraintMasterRepository(connection)
        calendars = SQLiteCalendarMasterRepository(connection)
        calendar_assignments = SQLiteCalendarAssignmentRepository(connection)
        calendar_snapshots = SQLiteCalendarSnapshotRepository(connection)
        resource_assignments = SQLiteP6ResourceAssignmentRepository(connection)
        resource_periods = SQLiteP6ResourceAssignmentPeriodRepository(connection)
        resource_spreads = SQLiteP6ResourceSpreadRepository(connection)
        capacities = SQLiteP6ResourceCapacityRepository(connection)
        capacity_service = P6ResourceCapacityApplicationService(
            capacities, transaction_manager
        )
        settings = SQLiteProjectScheduleSettingsRepository(connection)
        fields = SQLiteP6FieldRegistryRepository(connection)
        field_service = P6FieldRegistryApplicationService(fields, transaction_manager)
        udfs = SQLiteP6UserDefinedFieldRepository(connection)
        udf_service = P6UserDefinedFieldApplicationService(udfs, transaction_manager)
        mappings = SQLiteP6MappingRegistryRepository(connection)
        mapping_service = P6MappingRegistryApplicationService(
            mappings, transaction_manager
        )
        layouts = SQLiteP6LayoutRepository(connection)
        snapshots = SQLiteScheduleInputSnapshotRepository(connection)
        contexts = SQLiteCalculationContextRepository(connection)
        return cls(
            activities=activities,
            relationships=relationships,
            constraints=constraints,
            calendars=calendars,
            calendar_assignments=calendar_assignments,
            calendar_snapshots=calendar_snapshots,
            resource_assignments=resource_assignments,
            resource_periods=resource_periods,
            resource_spreads=resource_spreads,
            capacities=capacities,
            capacity_service=capacity_service,
            settings=settings,
            fields=fields,
            field_service=field_service,
            udfs=udfs,
            udf_service=udf_service,
            mappings=mappings,
            mapping_service=mapping_service,
            layouts=layouts,
            snapshots=snapshots,
            contexts=contexts,
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
            label=None,
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


class PreviewProjectInitializer:
    """Initialise a newly-created project with real presentation metadata."""

    def __init__(self, repositories: PreviewRepositories) -> None:
        self.repositories = repositories

    def __call__(self, scope: BackendScope) -> None:
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


def _to_activity(scope: BackendScope, item) -> ActivityMaster:
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
        activity_type=item.activity_type,
        status=item.status,
        status_code=item.status_code,
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

    for item in fixture.activities:
        repositories.activities.save(_to_activity(scope, item))
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
    for fixture in DEMO_PROJECTS:
        seed_demo_project(repositories, store, fixture)
    connection.commit()


def build_calendar_registry(connection: sqlite3.Connection) -> CalendarResolverRegistry:
    """Read every persisted calendar snapshot into one fail-closed registry."""

    for table in ("calendar_exception", "calendar_work_hour_rule"):
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if exists is not None:
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            if count is not None and int(count[0]) > 0:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_OVERRIDES_UNSUPPORTED",
                    "The preview registry does not silently ignore persisted "
                    "calendar exceptions or work-hour rules.",
                )

    scopes = connection.execute(
        "SELECT DISTINCT tenant_id, project_id, project_revision FROM calendar_master "
        "ORDER BY tenant_id, project_id, project_revision"
    ).fetchall()
    master_repository = SQLiteCalendarMasterRepository(connection)
    snapshot_repository = SQLiteCalendarSnapshotRepository(connection)
    day_resolvers: dict[str, WorkingTimeResolver] = {}
    canonical_by_key: dict[str, dict[str, object]] = {}

    for tenant_id, project_id, revision in scopes:
        scope = BackendScope(str(tenant_id), str(project_id), int(revision))
        for calendar in master_repository.list(scope):
            if calendar.base_calendar_id is not None or calendar.base_calendar_version is not None:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_INHERITANCE_UNSUPPORTED",
                    f"Calendar inheritance is not previewed: {calendar.calendar_id}@"
                    f"{calendar.calendar_version}.",
                )
            if calendar.kind != "working-day":
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_KIND_UNSUPPORTED",
                    "The local preview currently supports working-day calendars only.",
                )
            record = snapshot_repository.get(calendar)
            if record is None:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_SNAPSHOT_MISSING",
                    f"No immutable snapshot exists for {calendar.calendar_id}@"
                    f"{calendar.calendar_version}.",
                )
            try:
                working = WorkingCalendar.from_canonical_snapshot(record.snapshot)
            except (TypeError, ValueError) as exc:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_SNAPSHOT_INVALID",
                    f"Calendar snapshot for {calendar.calendar_id}@"
                    f"{calendar.calendar_version} is invalid.",
                ) from exc
            canonical = working.canonical_snapshot()
            key = f"{calendar.calendar_id}@{calendar.calendar_version}"
            existing = canonical_by_key.get(key)
            if existing is not None and existing != canonical:
                raise PreviewRuntimeError(
                    "PREVIEW_CALENDAR_CONFLICT",
                    f"Calendar key {key} resolves to different snapshots in two scopes.",
                )
            canonical_by_key[key] = canonical
            day_resolvers[key] = WorkingTimeResolver(working)

    return CalendarResolverRegistry(day_resolvers=day_resolvers)


@dataclass(frozen=True)
class PreviewWorkspaceReadProvider:
    """Build the authorized workspace envelope from persisted preview state."""

    activity_repository: object
    field_service: object
    layout_repository: object
    schedule_facts_provider: WorkspaceScheduleFactsProvider
    store: PreviewStore

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
        wbs = self.store.wbs_for(scope.tenant_id, scope.project_id)
        provider = PersistedWorkspaceReadProvider(
            activity_repository=self.activity_repository,  # type: ignore[arg-type]
            field_service=self.field_service,
            layout_repository=self.layout_repository,
            schedule_facts_provider=self.schedule_facts_provider,
            wbs_by_activity=wbs,
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
        if proposal.tool_name == "quantity.takeoff.create":
            return proposal.resource_domain == "quantity_takeoff" and bool(
                {"planner", "project_admin"} & set(active_session.roles)
            )
        if proposal.tool_name == "resource.assignment.create":
            return proposal.resource_domain == "resources" and bool(
                {"planner", "project_admin"} & set(active_session.roles)
            )
        if proposal.tool_name == "form.definition.create":
            return proposal.resource_domain == "forms" and bool(
                {"planner", "project_admin"} & set(active_session.roles)
            )
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
        return {
            "status": "ok",
            "mode": "local-full-stack-preview",
            "seed_version": PREVIEW_SEED_VERSION,
            "tenant_id": PREVIEW_TENANT_ID,
            "project_count": len(projects),
            "demo_project_count": sum(1 for item in projects if item["demo"]),
            "activity_count": int(activity_count[0]) if activity_count else 0,
            "capacity_segment_count": int(capacity_count[0]) if capacity_count else 0,
            "session_count": self.sessions.count(),
            "assistant": {
                "enabled": self.ai_assistant_enabled,
                "provider_configured": self.ai_assistant_enabled and bool(os.environ.get("CUBI_AI_LOCAL_MODEL", "").strip()),
                "provider_kind": os.environ.get("CUBI_AI_PROVIDER", "local-ollama"),
                "provider_environment_complete": bool(os.environ.get("CUBI_AI_LOCAL_MODEL", "").strip()),
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
    workspace_provider = PreviewWorkspaceReadProvider(
        activity_repository=repositories.activities,
        field_service=repositories.field_service,
        layout_repository=repositories.layouts,
        schedule_facts_provider=facts_provider,
        store=store,
    )
    workspace_service = WorkspaceControlRoomReadService(workspace_provider, policy)
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
    )

    ai_assistant_enabled = os.environ.get("CUBI_AI_ENABLED", "").strip().lower() in {
        "1", "true", "yes",
    }
    ai_assistant_provider = None
    ai_action_runtime = None
    ai_tool_names: tuple[str, ...] = ()
    if ai_assistant_enabled and os.environ.get("CUBI_AI_LOCAL_MODEL", "").strip():
        # Compose real tools only when the local model is configured; no remote fallback.
        # An enabled flag without model assets leaves assistant turns unavailable, not the site.
        ai_assistant_provider = build_ai_chat_provider_from_environment()
        action_store = SQLiteAIActionRuntimeStore(connection)
        idempotency_store = SQLiteAIActionExecutionIdempotencyStore(connection)
        permission_adapter = PreviewAIPermissionAdapter(sessions, store)
        activity_api = P6ActivityMasterAPI(repositories.activities, policy)
        relationship_api = P6RelationshipAPI(repositories.relationships, policy)
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
        takeoff_repository = SQLiteQuantityTakeoffRepository(connection)
        quantity_takeoff_tool = build_quantity_takeoff_create_tool(
            repository=takeoff_repository,
            idempotency_store=idempotency_store,
        )
        tools = [activity_tool, project_plan_tool, quantity_takeoff_tool]
        assignment_service = P6ResourceAssignmentApplicationService(
            repositories.resource_assignments, repositories.transaction_manager
        )
        assignment_period_service = P6ResourceAssignmentPeriodApplicationService(
            repositories.resource_periods, repositories.transaction_manager
        )
        spread_service = P6ResourceSpreadApplicationService(
            repositories.resource_spreads, repositories.transaction_manager
        )
        resource_read_api = P6ResourceReadAPI(
            assignment_service, assignment_period_service, spread_service, policy
        )
        resource_write_api = P6ResourceWriteAPI(
            assignment_period_service, policy, assignment_service
        )
        from construction_pm.ai_action_resource_tools import build_resource_assignment_create_tool

        resource_assignment_tool = build_resource_assignment_create_tool(
            activity_api=activity_api,
            resource_write_api=resource_write_api,
            resource_read_api=resource_read_api,
            idempotency_store=idempotency_store,
            transaction_manager=repositories.transaction_manager,
        )
        tools.append(resource_assignment_tool)
        form_repository = SQLiteFormBuilderRepository(connection)
        form_builder_api = FormBuilderAPI(
            form_repository,
            policy,
            repositories.transaction_manager,
            clock=lambda: datetime.now(timezone.utc),
        )
        from construction_pm.ai_action_form_tools import build_form_definition_create_tool

        form_definition_tool = build_form_definition_create_tool(
            form_api=form_builder_api,
            idempotency_store=idempotency_store,
            transaction_manager=repositories.transaction_manager,
        )
        tools.append(form_definition_tool)
        ai_action_runtime = AIActionRuntime(
            store=action_store,
            permission_adapter=permission_adapter,
            audit_sink=action_store,
            tools=tuple(tools),
            clock=lambda: datetime.now(timezone.utc),
            transaction_manager=repositories.transaction_manager,
        )
        ai_tool_names = (
            "activity.create",
            "project.plan.create",
            "quantity.takeoff.create",
            "resource.assignment.create",
            "form.definition.create",
        )

    app = build_project_lifecycle_wsgi_app(
        lifecycle_api=lifecycle_api,
        snapshot_repository=repositories.snapshots,
        calendar_registry_factory=lambda: build_calendar_registry(connection),
        calculation_context_repository=repositories.contexts,
        authorization_policy=policy,
        activity_master_repository=repositories.activities,
        relationship_master_repository=repositories.relationships,
        schedule_snapshot_publication_api=snapshot_api,
        backend_p0_api=backend_api,
        form_builder_api=form_builder_api if ai_assistant_enabled and os.environ.get("CUBI_AI_LOCAL_MODEL", "").strip() else None,
        p6_field_registry_api=P6FieldRegistryAPI(
            repositories.field_service,
            repositories.udf_service,
            policy,
        ),
        p6_layout_definition_api=P6LayoutDefinitionAPI(repositories.layouts, policy),
        p6_formula_authority_api=P6FormulaAuthorityAPI(
            repositories.field_service,
            policy,
        ),
        p6_calendar_read_api=P6CalendarReadAPI(
            repositories.calendars,
            repositories.calendar_snapshots,
            policy,
        ),
        p6_interchange_api=P6InterchangeAPI(
            mapping_service=repositories.mapping_service,
            authorization_policy=policy,
            codecs={PREVIEW_INTERCHANGE_FORMAT: P6PrimaveraXmlCodec()},
        ),
        p6_resource_capacity_read_api=P6ResourceCapacityReadAPI(
            repositories.capacity_service,
            policy,
        ),
        p6_resource_capacity_write_api=P6ResourceCapacityWriteAPI(
            repositories.capacity_service,
            policy,
            clock=PreviewClock(),
        ),
        clock=PreviewClock(),
        ai_action_runtime=ai_action_runtime,
        ai_assistant_provider=ai_assistant_provider,
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
]
