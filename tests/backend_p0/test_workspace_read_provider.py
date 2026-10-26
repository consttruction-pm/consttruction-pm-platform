from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import ActivityMaster, SQLiteActivityMasterRepository
from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.authoritative_schedule_facts import PublishedScheduleFactsProvider
from construction_pm.backend_p0.authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.backend_p0.workspace_read import (
    WORKSPACE_CONTROL_ROOM_READ_VERSION,
    WorkspaceControlRoomReadService,
)
from construction_pm.backend_p0.workspace_read_provider import PersistedWorkspaceReadProvider
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
    SQLiteP6FieldRegistryRepository,
)
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    SQLiteP6LayoutRepository,
)
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import CalendarReference, CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.time_duration import DurationUnit


SCOPE = BackendScope("tenant-demo", "project-demo", 1)
AUTH = AuthorizationContext("tenant-demo", "project-demo", "user-demo", frozenset({"viewer"}))


def _activity(scope: BackendScope, activity_id: str, name: str, duration: int = 2) -> ActivityMaster:
    return ActivityMaster(
        scope=scope,
        activity_id=activity_id,
        duration_value=Decimal(duration),
        duration_unit=DurationUnit.WORKING_DAY,
        name=name,
        percent_complete=25.0,
    )


def _fixture(connection: sqlite3.Connection):
    activity_repository = SQLiteActivityMasterRepository(connection)
    transaction_manager = SQLiteTransactionManager(connection)
    field_service = P6FieldRegistryApplicationService(
        SQLiteP6FieldRegistryRepository(connection),
        transaction_manager,
    )
    for field_id in (
        "activity.activity_id",
        "activity.activity_name",
        "activity.early_start",
        "activity.early_finish",
        "activity.total_float",
        "activity.is_critical",
    ):
        field_service.save_field(
            PersistedP6Field(SCOPE, "p6-field-registry.v1", get_field(field_id))
        )
    layout_repository = SQLiteP6LayoutRepository(connection)
    layout_repository.upsert(
        PersistedP6Layout(
            SCOPE,
            "project",
            "activity",
            1,
            (
                LayoutColumn("activity.activity_name", True, 0, None, 260, "start", False, False),
                LayoutColumn("activity.early_start", True, 1, None, 120, "end", False, False),
                LayoutColumn("activity.total_float", True, 2, None, 100, "end", False, False),
                LayoutColumn("activity.is_critical", True, 3, None, 90, "center", False, False),
            ),
            {},
        )
    )
    activity_repository.save(_activity(SCOPE, "A-1", "Excavation", 2))
    activity_repository.save(_activity(SCOPE, "A-2", "Concrete", 3))
    # Other scope rows must never leak into the projection.
    activity_repository.save(_activity(BackendScope("tenant-demo", "project-demo", 2), "A-9", "Future", 1))
    activity_repository.save(_activity(BackendScope("tenant-other", "project-demo", 1), "A-8", "Other", 1))
    return activity_repository, field_service, layout_repository


FACTS = {
    "activities": {
        "A-1": {
            "start": "2026-10-19",
            "finish": "2026-10-20",
            "duration": 2,
            "critical": True,
            "early_start": "2026-10-19",
            "early_finish": "2026-10-20",
            "late_start": "2026-10-21",
            "late_finish": "2026-10-22",
            "total_float": 2,
            "free_float": 0,
        },
        "A-2": {
            "start": "2026-10-21",
            "finish": "2026-10-23",
            "duration": 3,
            "critical": False,
            "early_start": "2026-10-21",
            "early_finish": "2026-10-23",
            "late_start": "2026-10-26",
            "late_finish": "2026-10-28",
            "total_float": 3,
            "free_float": 3,
        },
    },
    "project_finish": "2026-10-23",
}


def test_provider_joins_scoped_activities_layout_and_shared_core_facts() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        activity_repository, field_service, layout_repository = _fixture(connection)
        received: list[tuple[BackendScope, AuthorizationContext | None]] = []

        def facts(scope: BackendScope, auth_context: AuthorizationContext | None):
            received.append((scope, auth_context))
            return FACTS

        provider = PersistedWorkspaceReadProvider(
            activity_repository=activity_repository,
            field_service=field_service,
            layout_repository=layout_repository,
            schedule_facts_provider=facts,
            wbs_by_activity={"A-1": "WBS-1 Site works", "A-2": "WBS-1 Site works"},
        )
        snapshot = provider.read(SCOPE, auth_context=AUTH)

        assert snapshot is not None
        assert snapshot["contract_version"] == WORKSPACE_CONTROL_ROOM_READ_VERSION
        assert snapshot["context"] == {
            "tenant_id": "tenant-demo",
            "project_id": "project-demo",
            "revision": 1,
        }
        assert received == [(SCOPE, AUTH)]
        workspace = snapshot["workspace"]
        assert workspace["contract_version"] == "workspace-control-room.v1"
        assert [column["id"] for column in workspace["columns"]] == [
            "activity.activity_name",
            "activity.early_start",
            "activity.total_float",
            "activity.is_critical",
        ]
        assert workspace["columns"][0]["label"] == "Activity Name"
        assert workspace["columns"][1]["data_type"] == "date"
        assert workspace["columns"][3]["data_type"] == "boolean"
        assert [row["id"] for row in workspace["activities"]] == ["A-1", "A-2"]
        assert workspace["wbs_summary"] == [
            {
                "wbs_id": "WBS-1 Site works",
                "activity_count": 2,
                "critical_count": 1,
                "scheduled_start": "2026-10-19",
                "scheduled_finish": "2026-10-23",
                "total_float_min": 2,
            }
        ]
        first = workspace["activities"][0]
        assert first["wbs_id"] == "WBS-1 Site works"
        assert first["code"] == "A-1"
        assert first["name"] == "Excavation"
        assert first["gantt"] == {
            "start": "2026-10-19",
            "finish": "2026-10-20",
            "progressPercent": 25.0,
            "critical": True,
        }
        assert first["cells"]["activity.early_start"] == "2026-10-19"
        assert first["cells"]["activity.total_float"] == 2
        assert first["cells"]["activity.is_critical"] is True
        assert first["cells"]["activity.planned_duration"] == "2"
        # Canonical field-registry IDs always carry the same values as the
        # legacy compatibility aliases so a persisted canonical layout is not
        # rendered as blank cells.
        assert first["cells"]["activity.id"] == "A-1"
        assert first["cells"]["activity.name"] == "Excavation"
        assert first["cells"]["activity.status"] == "Not Started"
        assert first["cells"]["activity.type"] == "Task Dependent"
        assert first["cells"]["activity.wbs"] == "WBS-1 Site works"
        assert first["cells"]["activity.activity_name"] == first["cells"]["activity.name"]
        assert first["cells"]["activity.activity_status"] == first["cells"]["activity.status"]
        for key in (
            "field_daily_logs",
            "field_issues",
            "field_timecards",
            "equipment_status_reports",
            "inspections",
            "quality_records",
            "safety_observations",
            "punch_items",
        ):
            assert snapshot[key] == []
    finally:
        connection.close()


def test_provider_rolls_up_wbs_groups_in_first_appearance_order() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        activity_repository, field_service, layout_repository = _fixture(connection)
        activity_repository.save(_activity(SCOPE, "A-3", "Closeout", 1))
        facts = {"activities": {"A-1": dict(FACTS["activities"]["A-1"])}}
        provider = PersistedWorkspaceReadProvider(
            activity_repository=activity_repository,
            field_service=field_service,
            layout_repository=layout_repository,
            schedule_facts_provider=lambda scope, auth: facts,
            wbs_by_activity={"A-1": "WBS-1 Civil", "A-2": "WBS-2 MEP"},
        )
        summary = provider.read(SCOPE)["workspace"]["wbs_summary"]

        assert summary == [
            {
                "wbs_id": "WBS-1 Civil",
                "activity_count": 1,
                "critical_count": 1,
                "scheduled_start": "2026-10-19",
                "scheduled_finish": "2026-10-20",
                "total_float_min": 2,
            },
            {
                "wbs_id": "WBS-2 MEP",
                "activity_count": 1,
                "critical_count": 0,
                "scheduled_start": None,
                "scheduled_finish": None,
                "total_float_min": None,
            },
            {
                "wbs_id": "UNASSIGNED",
                "activity_count": 1,
                "critical_count": 0,
                "scheduled_start": None,
                "scheduled_finish": None,
                "total_float_min": None,
            },
        ]
    finally:
        connection.close()


def test_provider_without_snapshot_keeps_activities_but_fabricates_no_dates() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        activity_repository, field_service, layout_repository = _fixture(connection)
        provider = PersistedWorkspaceReadProvider(
            activity_repository=activity_repository,
            field_service=field_service,
            layout_repository=layout_repository,
            schedule_facts_provider=lambda scope, auth: None,
        )
        workspace = provider.read(SCOPE)["workspace"]
        for activity in workspace["activities"]:
            assert activity["gantt"] is None
            assert "start" not in activity["cells"]
            assert "activity.early_start" not in activity["cells"]
            assert "activity.is_critical" not in activity["cells"]
        assert workspace["wbs_summary"] == [
            {
                "wbs_id": "UNASSIGNED",
                "activity_count": 2,
                "critical_count": 0,
                "scheduled_start": None,
                "scheduled_finish": None,
                "total_float_min": None,
            }
        ]
    finally:
        connection.close()


def test_provider_rejects_criticality_missing_from_a_scheduled_fact() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        activity_repository, field_service, layout_repository = _fixture(connection)
        provider = PersistedWorkspaceReadProvider(
            activity_repository=activity_repository,
            field_service=field_service,
            layout_repository=layout_repository,
            schedule_facts_provider=lambda scope, auth: {
                "activities": {"A-1": {"start": "2026-10-19", "finish": "2026-10-20"}}
            },
        )
        with pytest.raises(ValueError, match="INVALID_SCHEDULE_FACT_CRITICAL"):
            provider.read(SCOPE)
    finally:
        connection.close()


def test_workspace_service_authorizes_before_invoking_the_persisted_provider() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        activity_repository, field_service, layout_repository = _fixture(connection)
        calls: list[BackendScope] = []

        def facts(scope: BackendScope, auth_context: AuthorizationContext | None):
            calls.append(scope)
            return FACTS

        provider = PersistedWorkspaceReadProvider(
            activity_repository=activity_repository,
            field_service=field_service,
            layout_repository=layout_repository,
            schedule_facts_provider=facts,
        )
        policy = RoleBasedAuthorizationPolicy(
            {"viewer": frozenset({Permission.PROJECT_READ})}
        )
        service = WorkspaceControlRoomReadService(provider, policy)
        allowed = service.read(SCOPE, auth_context=AUTH)
        assert allowed is not None
        assert len(calls) == 1

        denied = AuthorizationContext(
            "tenant-demo", "project-demo", "user-demo", frozenset({"unassigned"})
        )
        with pytest.raises(Exception) as exc:
            service.read(SCOPE, auth_context=denied)
        assert getattr(exc.value, "code") == "FORBIDDEN"
        assert len(calls) == 1
    finally:
        connection.close()


def _schedule_input(snapshot_id: str, duration: int) -> AuthoritativeScheduleInput:
    return AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id=SCOPE.tenant_id,
        project_id=SCOPE.project_id,
        project_revision=SCOPE.project_revision,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A-1", duration),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )


def _context(snapshot_id: str, now: datetime) -> CalculationContext:
    return CalculationContext(
        project_id=SCOPE.project_id,
        project_version=SCOPE.project_revision,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-test",
        engine_version="engine-test",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id=snapshot_id,
        tenant_id=SCOPE.tenant_id,
        actor_id="authoritative-actor",
    )


def test_published_facts_provider_selects_newest_snapshot_and_uses_shared_core() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        snapshots = SQLiteScheduleInputSnapshotRepository(connection)
        contexts = SQLiteCalculationContextRepository(connection)
        earlier = datetime(2026, 9, 30, 8, tzinfo=timezone.utc)
        later = earlier + timedelta(hours=1)
        for snapshot_id, duration, created_at in (
            ("SNAP-1", 2, earlier),
            ("SNAP-2", 3, later),
        ):
            source = _schedule_input(snapshot_id, duration)
            context = _context(snapshot_id, created_at)
            snapshots.save(build_snapshot(source, context, created_at))
            contexts.save(build_persisted_context(SCOPE, context))

        registry = CalendarResolverRegistry(
            day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
        )
        query_provider = AuthoritativeScheduleQueryProvider(
            snapshot_repository=snapshots,
            calendar_registry_factory=lambda: registry,
            calculation_context_repository=contexts,
        )
        facts = PublishedScheduleFactsProvider(snapshots, query_provider)

        assert facts.latest_snapshot_id(SCOPE) == "SNAP-2"
        payload = facts(SCOPE, AUTH)
        assert payload is not None
        assert payload["activity_count"] == 1
        assert payload["activities"]["A-1"]["start"] == "2026-09-21"
        assert payload["activities"]["A-1"]["finish"] == "2026-09-23"
        assert payload["activities"]["A-1"]["critical"] is True
        assert payload["project_finish"] == "2026-09-23"

        other = BackendScope(SCOPE.tenant_id, SCOPE.project_id, 2)
        assert facts(other, AUTH) is None
    finally:
        connection.close()


def test_published_facts_provider_returns_none_when_no_snapshot_was_published() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        snapshots = SQLiteScheduleInputSnapshotRepository(connection)
        contexts = SQLiteCalculationContextRepository(connection)
        provider = PublishedScheduleFactsProvider(
            snapshots,
            AuthoritativeScheduleQueryProvider(
                snapshot_repository=snapshots,
                calendar_registry_factory=lambda: CalendarResolverRegistry(),
                calculation_context_repository=contexts,
            ),
        )
        assert provider(SCOPE, AUTH) is None
    finally:
        connection.close()
