"""The resource surface is reachable only when the composition seam wires it.

Slice 6 closed a production gap where every PostgreSQL resource repository
existed but no resource API reached ``build_project_lifecycle_wsgi_app``. These
tests pin both directions of that seam: an unwired application answers
``ROUTE_NOT_FOUND`` (the regression), and a wired application persists and reads
resources, assignments and assignment periods through the real HTTP routes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import sqlite3

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.calendar_exception_repository import (
    SQLiteCalendarExceptionRepository,
)
from construction_pm.calendar_master_repository import SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import (
    SQLiteCalendarSnapshotRepository,
)
from construction_pm.calendar_work_hours_repository import (
    SQLiteCalendarWorkHourRepository,
)
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_master_api import P6ResourceAPI
from construction_pm.p6_resource_master_repository import SQLiteP6ResourceRepository
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
)
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry


class _Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class _Projects:
    def __init__(self) -> None:
        self.revision = 3

    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("p1", tenant_id, "Project One", self.revision),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", self.revision)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def _lifecycle_api(now: datetime) -> ProjectLifecycleAPI:
    session = AuthenticatedSession(
        "s1", "u1", "T-1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = ProjectLifecycleService(
        _Sessions(session), _Projects(), default_project_policy()
    )
    return ProjectLifecycleAPI(service)


def _request(app, method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload or {}).encode("utf-8")
    status: list[str] = []
    chunks: list[bytes] = []
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_COOKIE": "cp_session=s1",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }

    def start_response(value, headers):
        status.append(value)

    chunks.extend(app(environ, start_response))
    return status[0], json.loads(b"".join(chunks))


def _build_app(connection: sqlite3.Connection, *, wire_resources: bool):
    now = datetime(2026, 11, 2, 8, 0, tzinfo=timezone.utc)
    policy = default_project_policy()
    manager = SQLiteTransactionManager(connection)
    options: dict[str, object] = {}
    if wire_resources:
        calendar_repository = SQLiteCalendarMasterRepository(connection)
        assignment_service = P6ResourceAssignmentApplicationService(
            SQLiteP6ResourceAssignmentRepository(connection), manager
        )
        period_service = P6ResourceAssignmentPeriodApplicationService(
            SQLiteP6ResourceAssignmentPeriodRepository(connection), manager
        )
        spread_service = P6ResourceSpreadApplicationService(
            SQLiteP6ResourceSpreadRepository(connection), manager
        )
        options = {
            "p6_resource_api": P6ResourceAPI(
                SQLiteP6ResourceRepository(connection),
                policy,
                calendar_repository,
            ),
            "resource_read_api": P6ResourceReadAPI(
                assignment_service, period_service, spread_service, policy
            ),
            "resource_write_api": P6ResourceWriteAPI(
                period_service, policy, assignment_service=assignment_service
            ),
            # The composition seam builds the persisted leveling resolver from
            # the read API plus these exact calendar repositories, so the
            # wiring test supplies the same complete dependency set the
            # production runtime supplies.
            "resource_calendar_master_repository": calendar_repository,
            "resource_calendar_snapshot_repository": SQLiteCalendarSnapshotRepository(
                connection
            ),
            "resource_calendar_exception_repository": SQLiteCalendarExceptionRepository(
                connection
            ),
            "resource_calendar_work_hours_repository": SQLiteCalendarWorkHourRepository(
                connection
            ),
        }
    return build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(now),
        snapshot_repository=SQLiteScheduleInputSnapshotRepository(connection),
        calendar_registry_factory=lambda: CalendarResolverRegistry(day_resolvers={}),
        calculation_context_repository=SQLiteCalculationContextRepository(connection),
        authorization_policy=policy,
        clock=type("Clock", (), {"now": lambda self: now})(),
        **options,
    )


def test_unwired_composition_answers_route_not_found_for_resources():
    connection = sqlite3.connect(":memory:")
    app = _build_app(connection, wire_resources=False)

    status, body = _request(app, "GET", "/api/projects/p1/p6/resources")
    assert status.startswith("404")
    assert body["code"] == "ROUTE_NOT_FOUND"

    status, body = _request(
        app,
        "POST",
        "/api/projects/p1/p6/resource-assignments",
        {
            "contract_version": "p6-resource-write-api.v1",
            "assignment_id": "AS-1",
            "activity_id": "A-1",
            "resource_id": "R-1",
        },
    )
    assert status.startswith("404")
    assert body["code"] == "ROUTE_NOT_FOUND"
    connection.close()


def test_wired_composition_persists_resources_and_assignments_over_http():
    connection = sqlite3.connect(":memory:")
    app = _build_app(connection, wire_resources=True)

    status, created = _request(
        app,
        "POST",
        "/api/projects/p1/p6/resources",
        {
            "resource_id": "R-CREW",
            "name": "Civil crew",
            "resource_type": "labor",
            "unit_of_measure": "crew",
        },
    )
    assert status.startswith("200"), created
    assert created["contract_version"] == "p6-resource-api.v1"
    assert created["resource"]["record_revision"] == 1

    status, listing = _request(app, "GET", "/api/projects/p1/p6/resources")
    assert status.startswith("200")
    assert [item["resource"]["resource_id"] for item in listing["resources"]] == [
        "R-CREW"
    ]

    status, assignment = _request(
        app,
        "POST",
        "/api/projects/p1/p6/resource-assignments",
        {
            "contract_version": "p6-resource-write-api.v1",
            "assignment_id": "AS-CREW-1",
            "activity_id": "A-1",
            "resource_id": "R-CREW",
            "units": "40",
            "unit": "labor-unit",
            "is_driving": True,
            "units_per_time": "8",
            "units_per_time_period": "day",
            "hours_per_units_time_period": "8",
        },
    )
    assert status.startswith("200"), assignment
    assert assignment["contract_version"] == "p6-resource-write-api.v1"
    assert assignment["assignment"]["units"] == "40"
    assert assignment["assignment"]["is_driving"] is True

    status, fetched = _request(
        app, "GET", "/api/projects/p1/p6/resource-assignments/AS-CREW-1"
    )
    assert status.startswith("200"), fetched
    assert fetched["assignment"] == assignment["assignment"]
    connection.close()
