import json
from datetime import datetime, timedelta, timezone
import sqlite3

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    SQLiteCalendarMasterRepository,
)
from construction_pm.p6_resource_master_api import P6ResourceAPI
from construction_pm.p6_resource_master_repository import SQLiteP6ResourceRepository


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        return (
            ProjectSummary("p1", tenant_id, "Project One", 2)
            if project_id == "p1"
            else None
        )

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def routes(connection=None, roles=("project_admin",)):
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset(roles), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    connection = connection or sqlite3.connect(":memory:")
    calendars = SQLiteCalendarMasterRepository(connection)
    calendars.save(
        CalendarMaster(
            scope=BackendScope("t1", "p1", 2),
            calendar_id="CAL-1",
            calendar_version="v1",
            kind="working-day",
            name="Project calendar",
            calendar_type="project",
        )
    )
    resource_api = P6ResourceAPI(
        SQLiteP6ResourceRepository(connection),
        default_project_policy(),
        calendars,
    )
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_resource_api=resource_api,
    )
    router.connection = connection
    return router


def test_resource_http_create_read_list_and_update():
    r = routes()
    payload = {
        "resource_id": "R-CREW",
        "name": "Civil Crew",
        "resource_type": "labor",
        "calendar_id": "CAL-1",
        "default_units_per_time": "8",
        "unit_of_measure": "crew",
    }
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/resources",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode(),
    )
    assert status == 200
    created = json.loads(body)
    assert created["contract_version"] == "p6-resource-api.v1"
    assert created["resource"]["record_revision"] == 1

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/resources/R-CREW", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body) == created

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/resources", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body)["resources"] == [created]

    update = {"name": "Senior Civil Crew", "resource_type": "labor", "expected_revision": 1}
    status, _, body = r.handle(
        "PATCH",
        "/api/projects/p1/p6/resources/R-CREW",
        cookies={"cp_session": "s1"},
        body=json.dumps(update).encode(),
    )
    assert status == 200
    updated = json.loads(body)
    assert updated["resource"]["name"] == "Senior Civil Crew"
    assert updated["resource"]["record_revision"] == 2


def test_resource_http_hierarchy_conflicts_and_revision_guard():
    r = routes()
    child = {
        "resource_id": "R-CREW-A",
        "name": "Crew A",
        "resource_type": "labor",
        "parent_resource_id": "R-MISSING",
    }
    status, _, _ = r.handle(
        "POST",
        "/api/projects/p1/p6/resources",
        cookies={"cp_session": "s1"},
        body=json.dumps(child).encode(),
    )
    assert status == 409

    r.handle(
        "POST",
        "/api/projects/p1/p6/resources",
        cookies={"cp_session": "s1"},
        body=json.dumps({"resource_id": "R-1", "name": "One"}).encode(),
    )
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/resources",
        cookies={"cp_session": "s1"},
        body=json.dumps({"resource_id": "R-1", "name": "Overwrite"}).encode(),
    )
    assert status == 409
    assert json.loads(body)["code"] == "RESOURCE_ALREADY_EXISTS"
    status, _, body = r.handle(
        "PATCH",
        "/api/projects/p1/p6/resources/R-1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Stale", "expected_revision": 9}).encode(),
    )
    assert status == 409

    status, _, _ = r.handle(
        "PATCH",
        "/api/projects/p1/p6/resources/R-1",
        cookies={"cp_session": "s1"},
        body=b"{}",
    )
    assert status == 400


def test_resource_http_rejects_cross_project_and_malformed_body():
    r = routes()
    status, _, _ = r.handle(
        "GET", "/api/projects/other/p6/resources", cookies={"cp_session": "s1"}
    )
    assert status == 403
    status, _, _ = r.handle(
        "GET", "/api/projects/p1/p6/resources/missing", cookies={"cp_session": "s1"}
    )
    assert status == 404


def test_resource_http_rejects_unknown_calendar_reference():
    r = routes()
    payload = {
        "resource_id": "R-NO-CAL",
        "name": "Crew without calendar",
        "calendar_id": "CAL-MISSING",
    }
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/resources",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode(),
    )
    assert status == 409
    error = json.loads(body)
    assert error["code"] == "RESOURCE_CALENDAR_NOT_FOUND"

    payload["calendar_id"] = "CAL-1"
    status, _, _ = r.handle(
        "POST",
        "/api/projects/p1/p6/resources",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode(),
    )
    assert status == 200


def _create_resource(router, resource_id="R-DEL", **overrides):
    payload = {"resource_id": resource_id, "name": "Delete me"}
    payload.update(overrides)
    status, _, body = router.handle(
        "POST",
        "/api/projects/p1/p6/resources",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode(),
    )
    assert status == 200
    return json.loads(body)


def test_resource_http_delete_removes_an_unreferenced_resource():
    r = routes()
    _create_resource(r)

    status, _, body = r.handle(
        "DELETE",
        "/api/projects/p1/p6/resources/R-DEL",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 1}).encode(),
    )

    assert status == 200
    deleted = json.loads(body)
    assert deleted["kind"] == "p6_resource_deleted"
    assert deleted["deleted"] is True
    assert deleted["removed_rows"]["p6_resource_master"] == 1
    status, _, _ = r.handle(
        "GET", "/api/projects/p1/p6/resources/R-DEL", cookies={"cp_session": "s1"}
    )
    assert status == 404


def test_resource_http_delete_rejects_missing_stale_and_malformed_requests():
    r = routes()
    status, _, body = r.handle(
        "DELETE",
        "/api/projects/p1/p6/resources/R-MISSING",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 1}).encode(),
    )
    assert status == 404
    assert json.loads(body)["code"] == "RESOURCE_NOT_FOUND"

    _create_resource(r)
    status, _, body = r.handle(
        "DELETE",
        "/api/projects/p1/p6/resources/R-DEL",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 9}).encode(),
    )
    assert status == 409
    assert json.loads(body)["code"] == "REVISION_CONFLICT"

    for payload in ({}, {"expected_revision": 0}, {"expected_revision": True}, {"expected_revision": "1"}):
        status, _, _ = r.handle(
            "DELETE",
            "/api/projects/p1/p6/resources/R-DEL",
            cookies={"cp_session": "s1"},
            body=json.dumps(payload).encode(),
        )
        assert status == 400
    # None of the refused requests removed the row.
    status, _, _ = r.handle(
        "GET", "/api/projects/p1/p6/resources/R-DEL", cookies={"cp_session": "s1"}
    )
    assert status == 200


def test_resource_http_delete_reports_references_and_keeps_the_row():
    from construction_pm.p6_resource_assignment_repository import (
        SQLiteP6ResourceAssignmentRepository,
    )

    connection = sqlite3.connect(":memory:")
    SQLiteP6ResourceAssignmentRepository(connection)
    connection.execute(
        "INSERT INTO p6_resource_assignment "
        "(tenant_id,project_id,project_revision,assignment_id,activity_id,resource_id) "
        "VALUES ('t1','p1',2,'ASN-1','A-1','R-DEL')"
    )
    connection.commit()
    r = routes(connection=connection)
    _create_resource(r)

    status, _, body = r.handle(
        "DELETE",
        "/api/projects/p1/p6/resources/R-DEL",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 1}).encode(),
    )

    assert status == 409
    error = json.loads(body)
    assert error["code"] == "RESOURCE_IN_USE"
    assert error["details"]["dependencies"]["assignments"] == 1
    status, _, _ = r.handle(
        "GET", "/api/projects/p1/p6/resources/R-DEL", cookies={"cp_session": "s1"}
    )
    assert status == 200


def test_resource_http_delete_enforces_write_permission_and_project_scope():
    viewer = routes(roles=("viewer",))
    viewer.connection.execute(
        "INSERT INTO p6_resource_master "
        "(tenant_id,project_id,project_revision,resource_id,name,record_revision) "
        "VALUES ('t1','p1',2,'R-DEL','Delete me',1)"
    )
    viewer.connection.commit()

    status, _, body = viewer.handle(
        "DELETE",
        "/api/projects/p1/p6/resources/R-DEL",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 1}).encode(),
    )
    assert status == 403
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"

    admin = routes()
    status, _, _ = admin.handle(
        "DELETE",
        "/api/projects/other/p6/resources/R-DEL",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 1}).encode(),
    )
    assert status == 403
    status, _, _ = viewer.handle(
        "GET", "/api/projects/p1/p6/resources/R-DEL", cookies={"cp_session": "s1"}
    )
    assert status == 200
