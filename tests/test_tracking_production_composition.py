from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import sqlite3

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_master_repository import (
    P6Resource,
    SQLiteP6ResourceRepository,
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
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSMaster,
    WBSParentKind,
)


SCOPE = BackendScope("T-1", "P-1", 9)


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id: str, user_id: str) -> tuple[ProjectSummary, ...]:
        return (ProjectSummary("P-1", tenant_id, "Project One", 9),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "P-1":
            return None
        return ProjectSummary("P-1", tenant_id, "Project One", 9)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def _lifecycle_api(now: datetime, permissions: frozenset[str]) -> ProjectLifecycleAPI:
    from construction_pm.application.project_lifecycle import ProjectLifecycleService

    session = AuthenticatedSession(
        "s1", "u1", "T-1", permissions, now + timedelta(hours=1)
    )
    service = ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    return ProjectLifecycleAPI(service)


def _publish_snapshot(
    conn: sqlite3.Connection, now: datetime
) -> tuple[SQLiteScheduleInputSnapshotRepository, SQLiteCalculationContextRepository]:
    snapshot_repo = SQLiteScheduleInputSnapshotRepository(conn)
    context_repo = SQLiteCalculationContextRepository(conn)
    source = AuthoritativeScheduleInput(
        snapshot_id="S-TRACK",
        tenant_id="T-1",
        project_id="P-1",
        project_revision=9,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference("CAL-1", "1"),
        activities=(Activity("A-1", 2),),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id="P-1",
        project_version=9,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id="S-TRACK",
        tenant_id="T-1",
        actor_id="u1",
    )
    snapshot_repo.save(build_snapshot(source, context, now))
    context_repo.save(build_persisted_context(SCOPE, context))
    return snapshot_repo, context_repo


def _seed_facts(conn: sqlite3.Connection) -> None:
    wbs = SQLiteWBSMasterRepository(conn)
    wbs.save(
        WBSMaster(SCOPE, "W-1", WBSParentKind.PROJECT, None, "1", "Site work", 1)
    )
    SQLiteActivityMasterRepository(conn).save(
        ActivityMaster(
            scope=SCOPE,
            activity_id="A-1",
            duration_value=Decimal("2"),
            duration_unit=DurationUnit.WORKING_DAY,
            actual_start=date(2026, 9, 21),
            expected_finish=date(2026, 9, 23),
            name="Excavate",
            wbs_id="W-1",
        )
    )
    SQLiteP6ResourceRepository(conn).save(
        P6Resource(
            "T-1", "P-1", 9, "R-1", "Excavator", resource_type="nonlabor"
        )
    )
    SQLiteP6ResourceAssignmentRepository(conn).upsert(
        P6ResourceAssignment(
            scope=SCOPE,
            assignment_id="RA-1",
            activity_id="A-1",
            resource_id="R-1",
            units=Decimal("12.5"),
            actual_units=Decimal("2.25"),
            remaining_units=Decimal("10.25"),
            planned_cost=Decimal("300.10"),
            actual_cost=Decimal("50.05"),
            remaining_cost=Decimal("250.05"),
            currency="USD",
        )
    )


def _app(
    conn: sqlite3.Connection,
    now: datetime,
    *,
    with_resource_sources: bool = True,
):
    snapshot_repo, context_repo = _publish_snapshot(conn, now)
    _seed_facts(conn)
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    kwargs = {}
    if with_resource_sources:
        kwargs = {
            "tracking_resource_assignment_repository": SQLiteP6ResourceAssignmentRepository(
                conn
            ),
            "tracking_resource_repository": SQLiteP6ResourceRepository(conn),
        }
    return build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now, frozenset({"project_admin"})),
        snapshot_repository=snapshot_repo,
        calendar_registry_factory=lambda: registry,
        calculation_context_repository=context_repo,
        authorization_policy=default_project_policy(),
        activity_master_repository=SQLiteActivityMasterRepository(conn),
        wbs_master_repository=SQLiteWBSMasterRepository(conn),
        clock=type("Clock", (), {"now": lambda self: now})(),
        **kwargs,
    )


def _read(app, path: str) -> tuple[str, dict]:
    status: list[str] = []
    body: list[bytes] = []
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "HTTP_COOKIE": "cp_session=s1",
        "QUERY_STRING": "",
    }
    body.extend(app(environ, lambda status_line, headers: status.append(status_line)))
    return status[0], json.loads(b"".join(body).decode("utf-8"))


def test_production_composition_projects_persisted_resource_facts():
    conn = sqlite3.connect(":memory:")
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    app = _app(conn, now)

    status, payload = _read(app, "/api/projects/P-1/tracking/read")

    assert status.startswith("200"), payload
    assert payload["contract_version"] == "tracking-read-model.v1"
    assert [row["activity_id"] for row in payload["rows"]] == ["A-1"]
    assert payload["rows"][0]["wbs_code"] == "1"
    analysis = payload["resource_analysis"]
    assert analysis["status"] == "available"
    resources = analysis["resources"]
    assert [item["resource_id"] for item in resources] == ["R-1"]
    item = resources[0]
    assert item["resource_name"] == "Excavator"
    assert item["assignment_count"] == 1
    assert item["planned_units"] == "12.5"
    assert item["actual_units"] == "2.25"
    assert item["remaining_units"] == "10.25"
    assert item["planned_cost"] == "300.10"
    assert item["actual_cost"] == "50.05"
    assert item["remaining_cost"] == "250.05"
    assert analysis["totals"]["planned_units"] == "12.5"
    assert analysis["totals"]["planned_cost"] == "300.10"


def test_production_composition_reports_missing_resource_source_explicitly():
    conn = sqlite3.connect(":memory:")
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    app = _app(conn, now, with_resource_sources=False)

    status, payload = _read(app, "/api/projects/P-1/tracking/read")

    assert status.startswith("200"), payload
    assert payload["resource_analysis"]["status"] == "unavailable"
    assert payload["resource_analysis"]["reason"] == "resource_assignment_source_not_configured"
    assert payload["resource_analysis"]["resources"] == []
    assert {"code": "TRACKING_RESOURCE_SOURCE_UNAVAILABLE"} in payload["warnings"]


def test_production_composition_does_not_leak_other_project_resources():
    conn = sqlite3.connect(":memory:")
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    other = BackendScope("T-1", "P-OTHER", 9)
    SQLiteP6ResourceRepository(conn).save(
        P6Resource("T-1", "P-OTHER", 9, "R-OTHER", "Other project", resource_type="labor")
    )
    SQLiteP6ResourceAssignmentRepository(conn).upsert(
        P6ResourceAssignment(
            scope=other,
            assignment_id="RA-OTHER",
            activity_id="A-OTHER",
            resource_id="R-OTHER",
            units=Decimal("99"),
        )
    )
    app = _app(conn, now)

    status, payload = _read(app, "/api/projects/P-1/tracking/read")

    assert status.startswith("200"), payload
    assert [item["resource_id"] for item in payload["resource_analysis"]["resources"]] == [
        "R-1"
    ]
    assert payload["resource_analysis"]["totals"]["planned_units"] == "12.5"


def test_production_composition_fails_closed_without_published_schedule():
    conn = sqlite3.connect(":memory:")
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    app = _app(conn, now)
    conn.execute("DELETE FROM schedule_input_snapshot")
    conn.commit()

    status, payload = _read(app, "/api/projects/P-1/tracking/read")

    assert status.startswith("409"), payload
    assert payload["code"] == "TRACKING_SCHEDULE_NOT_PUBLISHED"
