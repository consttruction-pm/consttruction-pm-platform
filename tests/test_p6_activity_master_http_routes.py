from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import sqlite3

from construction_pm.activity_master_repository import SQLiteActivityMasterRepository
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary, ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.scheduling.activity import ActivityLevelingPriority


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self) -> None:
        self.items = {"p1": ("p1", "Project One", 2)}

    def list_for_user(self, tenant_id: str, user_id: str):
        return tuple(
            ProjectSummary(project_id, tenant_id, name, revision)
            for project_id, (project_id, name, revision) in self.items.items()
        )

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        item = self.items.get(project_id)
        if item is None:
            return None
        return ProjectSummary(item[0], tenant_id, item[1], item[2])

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str):
        self.items[project_id] = (project_id, name, 0)
        return ProjectSummary(project_id, tenant_id, name, 0)


def _app(*, role: str = "project_admin", db_path: str = ":memory:"):
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({role}), now + timedelta(hours=1)
    )
    policy = default_project_policy()
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(Sessions(session), Projects(), policy)
    )
    connection = sqlite3.connect(db_path)
    repository = SQLiteActivityMasterRepository(connection)
    routes = ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_activity_master_api=P6ActivityMasterAPI(repository, policy),
    )
    return ProjectLifecycleWsgiApp(routes), repository, connection


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


def test_authenticated_activity_master_write_fresh_read_and_revision_conflict(tmp_path):
    db_path = str(tmp_path / "cubi-activity-master.sqlite")
    app, _repository, connection = _app(db_path=db_path)
    path = "/api/projects/p1/p6/activities"
    actual_start = "2026-10-01T09:15:30.123456+00:00"
    create_payload = {
        "contract_version": "p6-activity-master-api.v1",
        "activity_id": "A-1",
        "name": "Foundation Slab",
        "activity_type": "Resource Dependent",
        "status": "In Progress",
        "status_code": "Active",
        "duration_value": "12.50",
        "duration_unit": "working-day",
        "actual_start": actual_start,
        "actual_finish": None,
        "remaining_duration": 8,
        "remaining_start": "2026-10-05",
        "percent_complete": 35.5,
        "percent_complete_type": "DURATION",
        "expected_finish": "2026-10-21",
        "planned_finish": "2026-10-23",
        "leveling_priority": "High",
        "original_duration": 15,
    }

    status, created = _request(app, "POST", path, create_payload)
    assert status == "201 Created"
    assert created["activity"]["record_revision"] == 1
    assert created["activity"]["name"] == "Foundation Slab"
    assert created["activity"]["activity_type"] == "Resource Dependent"
    assert created["activity"]["status"] == "In Progress"
    assert created["activity"]["status_code"] == "Active"
    assert created["activity"]["duration_value"] == "12.50"
    assert created["activity"]["actual_start"] == actual_start
    assert created["activity"]["planned_finish"] == "2026-10-23"
    assert created["activity"]["leveling_priority"] == "High"
    assert created["activity"]["original_duration"] == 15

    # A separate connection proves the route persisted and committed real data.
    fresh_connection = sqlite3.connect(db_path)
    fresh_repository = SQLiteActivityMasterRepository(fresh_connection)
    persisted = fresh_repository.get(BackendScope("t1", "p1", 2), "A-1")
    assert persisted is not None
    assert persisted.actual_start == datetime.fromisoformat(actual_start)
    assert persisted.duration_value == Decimal("12.50")
    assert persisted.leveling_priority is ActivityLevelingPriority.HIGH
    assert persisted.original_duration == 15
    assert persisted.name == "Foundation Slab"
    assert persisted.activity_type.value == "Resource Dependent"
    assert persisted.status.value == "In Progress"
    assert persisted.status_code.value == "Active"
    fresh_connection.close()

    status, loaded = _request(app, "GET", path + "/A-1")
    assert status == "200 OK"
    assert loaded["activity"]["actual_start"] == actual_start
    status, listed = _request(app, "GET", path)
    assert status == "200 OK"
    assert [item["activity"]["activity_id"] for item in listed["activities"]] == ["A-1"]

    update_payload = {
        **create_payload,
        "planned_finish": "2026-10-24",
        "leveling_priority": "Lowest",
        "name": "Foundation Slab Complete",
        "activity_type": "Task Dependent",
        "status": "Completed",
        "status_code": "Inactive",
        "expected_revision": 1,
    }
    status, updated = _request(app, "PATCH", path + "/A-1", update_payload)
    assert status == "200 OK"
    assert updated["activity"]["record_revision"] == 2
    assert updated["activity"]["planned_finish"] == "2026-10-24"
    assert updated["activity"]["leveling_priority"] == "Lowest"
    assert updated["activity"]["name"] == "Foundation Slab Complete"
    assert updated["activity"]["activity_type"] == "Task Dependent"
    assert updated["activity"]["status"] == "Completed"
    assert updated["activity"]["status_code"] == "Inactive"

    # PATCH is partial: omitted fields must be retained, not reset to defaults.
    partial_payload = {
        "contract_version": "p6-activity-master-api.v1",
        "expected_revision": 2,
        "planned_finish": "2026-10-25",
    }
    status, partial = _request(app, "PATCH", path + "/A-1", partial_payload)
    assert status == "200 OK"
    assert partial["activity"]["record_revision"] == 3
    assert partial["activity"]["planned_finish"] == "2026-10-25"
    assert partial["activity"]["duration_value"] == "12.50"
    assert partial["activity"]["duration_unit"] == "working-day"
    assert partial["activity"]["actual_start"] == actual_start
    assert partial["activity"]["expected_finish"] == "2026-10-21"
    assert partial["activity"]["remaining_duration"] == 8
    assert partial["activity"]["percent_complete"] == 35.5
    assert partial["activity"]["percent_complete_type"] == "DURATION"
    assert partial["activity"]["leveling_priority"] == "Lowest"
    assert partial["activity"]["original_duration"] == 15
    assert partial["activity"]["name"] == "Foundation Slab Complete"
    assert partial["activity"]["activity_type"] == "Task Dependent"
    assert partial["activity"]["status"] == "Completed"
    assert partial["activity"]["status_code"] == "Inactive"

    # Explicit null clears an optional value; omission above preserved it.
    clear_payload = {
        "contract_version": "p6-activity-master-api.v1",
        "expected_revision": 3,
        "expected_finish": None,
    }
    status, cleared = _request(app, "PATCH", path + "/A-1", clear_payload)
    assert status == "200 OK"
    assert cleared["activity"]["record_revision"] == 4
    assert cleared["activity"]["expected_finish"] is None
    assert cleared["activity"]["planned_finish"] == "2026-10-25"
    assert cleared["activity"]["original_duration"] == 15

    status, conflict = _request(
        app, "PATCH", path + "/A-1", {**update_payload, "expected_revision": 1}
    )
    assert status == "409 Conflict"
    assert conflict["code"] == "REVISION_CONFLICT"

    connection.close()


def test_activity_master_route_enforces_read_write_permission():
    viewer_app, _repository, connection = _app(role="viewer")
    payload = {
        "contract_version": "p6-activity-master-api.v1",
        "activity_id": "A-1",
        "duration_value": "1",
        "duration_unit": "working-day",
    }
    status, error = _request(viewer_app, "POST", "/api/projects/p1/p6/activities", payload)
    assert status == "403 Forbidden"
    assert error["code"] == "authorization denied for permission=project.write"
    connection.close()
