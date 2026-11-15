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
from construction_pm.p6_wbs_master_api import P6WBSMasterAPI, P6_WBS_MASTER_API_VERSION
from construction_pm.wbs_master_repository import SQLiteWBSMasterRepository
from construction_pm.scheduling.activity import (
    ActivityDurationType,
    ActivityLevelingPriority,
)


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self) -> None:
        self.items = {"p1": ("p1", "Project One", 2)}
        self.default_activity_type = "Task Dependent"
        self.default_percent_complete_type = "DURATION"
        self.default_duration_type = "Fixed Duration & Units"
        self.default_cost_account_id = ""
        self.settings_revision = 0

    def list_for_user(self, tenant_id: str, user_id: str):
        return tuple(
            ProjectSummary(
                project_id,
                tenant_id,
                name,
                revision,
                default_activity_type=self.default_activity_type,
                default_percent_complete_type=self.default_percent_complete_type,
                default_duration_type=self.default_duration_type,
                default_cost_account_id=self.default_cost_account_id,
            )
            for project_id, (project_id, name, revision) in self.items.items()
        )

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        item = self.items.get(project_id)
        if item is None:
            return None
        return ProjectSummary(
            item[0],
            tenant_id,
            item[1],
            item[2],
            default_activity_type=self.default_activity_type,
            default_percent_complete_type=self.default_percent_complete_type,
            default_duration_type=self.default_duration_type,
            default_cost_account_id=self.default_cost_account_id,
        )

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        self.items[project_id] = (project_id, name, 0)
        return ProjectSummary(project_id, tenant_id, name, 0)

    def update_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        expected_revision: int,
        name: str,
        default_activity_type: str | None = None,
        default_percent_complete_type: str | None = None,
        default_duration_type: str | None = None,
        default_cost_account_id: str | None = None,
        **_,
    ):
        item = self.items.get(project_id)
        if item is None or expected_revision != self.settings_revision:
            return None
        self.settings_revision = expected_revision + 1
        if default_activity_type is not None:
            self.default_activity_type = default_activity_type
        if default_percent_complete_type is not None:
            self.default_percent_complete_type = default_percent_complete_type
        if default_duration_type is not None:
            self.default_duration_type = default_duration_type
        if default_cost_account_id is not None:
            self.default_cost_account_id = default_cost_account_id
        return self.get_for_user(tenant_id, project_id, user_id)

    def record_defaults_application_for_user(
        self,
        tenant_id: str,
        user_id: str,
        project_id: str,
        *,
        activity_id: str,
        applied_activity_type: str,
        applied_percent_complete_type: str,
        applied_duration_type: str,
        applied_cost_account_id: str,
        actor_user_id: str,
        recorded_at,
    ):
        from construction_pm.application.project_lifecycle import (
            ProjectDefaultsApplicationEvent,
        )

        event = ProjectDefaultsApplicationEvent(
            tenant_id=tenant_id,
            project_id=project_id,
            event_id=f"{project_id}@{activity_id}",
            activity_id=activity_id,
            applied_activity_type=applied_activity_type,
            applied_percent_complete_type=applied_percent_complete_type,
            applied_duration_type=applied_duration_type,
            applied_cost_account_id=applied_cost_account_id,
            actor_user_id=actor_user_id,
            recorded_at=recorded_at,
        )
        if not hasattr(self, "defaults_events"):
            self.defaults_events = []
        self.defaults_events.append(event)
        return event

    def defaults_history_for_user(self, tenant_id: str, project_id: str, user_id: str):
        return tuple(getattr(self, "defaults_events", ()))


class Lease:
    def __init__(self, holder: str | None) -> None:
        self.holder = holder

    def checked_out_by(self, scope):
        return self.holder


class CostAccounts:
    def __init__(self, account_ids=("CA-CIVIL",)):
        self.account_ids = set(account_ids)

    def get(self, scope, account_id, *, auth_context):
        if account_id in self.account_ids:
            return {"account_id": account_id}
        return None

    def cost_account_exists(self, tenant_id, project_id, project_revision, account_id):
        return account_id in self.account_ids


class WbsResponsibilityStore:
    def __init__(self):
        self.items = {}

    def get_wbs_responsibility(self, tenant_id, project_id, wbs_id):
        return self.items.get((tenant_id, project_id, wbs_id))

    def assign_wbs_responsibility(
        self, tenant_id, project_id, wbs_id, responsible_obs_id, *,
        actor_user_id, occurred_at, expected_revision=None,
    ):
        key = (tenant_id, project_id, wbs_id)
        current = self.items.get(key)
        if current is None:
            if expected_revision not in (None, 0):
                raise ValueError("P6_WBS_RESPONSIBILITY_REVISION_CONFLICT")
            revision = 1
        else:
            if expected_revision != current[1]:
                raise ValueError("P6_WBS_RESPONSIBILITY_REVISION_CONFLICT")
            revision = expected_revision + 1
        self.items[key] = (responsible_obs_id, revision)
        return revision


def _app(
    *,
    role: str = "project_admin",
    db_path: str = ":memory:",
    default_activity_type: str = "Task Dependent",
    default_percent_complete_type: str = "DURATION",
    default_duration_type: str = "Fixed Duration & Units",
    default_cost_account_id: str = "",
    cost_accounts: CostAccounts | None = None,
    checkout_holder: str | None = None,
):
    now = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({role}), now + timedelta(hours=1)
    )
    policy = default_project_policy()
    projects = Projects()
    projects.default_activity_type = default_activity_type
    projects.default_percent_complete_type = default_percent_complete_type
    projects.default_duration_type = default_duration_type
    projects.default_cost_account_id = default_cost_account_id
    accounts = cost_accounts or CostAccounts()
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(
            Sessions(session), projects, policy, cost_accounts=accounts
        )
    )
    connection = sqlite3.connect(db_path)
    repository = SQLiteActivityMasterRepository(connection)
    wbs_repository = SQLiteWBSMasterRepository(connection)
    wbs_responsibility_repository = WbsResponsibilityStore()
    routes = ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_activity_master_api=P6ActivityMasterAPI(
            repository, policy, checkout_lease=Lease(checkout_holder)
        ),
        p6_wbs_master_api=P6WBSMasterAPI(
            wbs_repository, policy, checkout_lease=Lease(checkout_holder),
            responsibility_repository=wbs_responsibility_repository,
        ),
        p6_cost_account_api=accounts,
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
    wbs_status, wbs_root = _request(
        app,
        "POST",
        "/api/projects/p1/p6/wbs",
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "wbs_id": "W-ROOT",
            "parent_kind": "project",
            "parent_wbs_id": None,
            "code": "1",
            "name": "Project Root",
            "sequence_number": 0,
        },
    )
    assert wbs_status == "201 Created"
    assert wbs_root["wbs"]["wbs_id"] == "W-ROOT"
    path = "/api/projects/p1/p6/activities"
    actual_start = "2026-10-01T09:15:30.123456+00:00"
    create_payload = {
        "contract_version": "p6-activity-master-api.v1",
        "activity_id": "A-1",
        "name": "Foundation Slab",
        "short_name": "CP-A1",
        "activity_type": "Resource Dependent",
        "status": "In Progress",
        "status_code": "Active",
        "duration_value": "12.50",
        "duration_unit": "working-day",
        "duration_type": "Fixed Units",
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
        "wbs_id": "W-ROOT",
    }

    status, created = _request(app, "POST", path, create_payload)
    assert status == "201 Created"
    assert created["activity"]["record_revision"] == 1
    assert created["activity"]["name"] == "Foundation Slab"
    assert created["activity"]["short_name"] == "CP-A1"
    assert created["activity"]["activity_type"] == "Resource Dependent"
    assert created["activity"]["status"] == "In Progress"
    assert created["activity"]["status_code"] == "Active"
    assert created["activity"]["duration_value"] == "12.50"
    assert created["activity"]["duration_type"] == "Fixed Units"
    assert created["activity"]["actual_start"] == actual_start
    assert created["activity"]["planned_finish"] == "2026-10-23"
    assert created["activity"]["leveling_priority"] == "High"
    assert created["activity"]["original_duration"] == 15
    assert created["activity"]["wbs_id"] == "W-ROOT"

    # A separate connection proves the route persisted and committed real data.
    fresh_connection = sqlite3.connect(db_path)
    fresh_repository = SQLiteActivityMasterRepository(fresh_connection)
    persisted = fresh_repository.get(BackendScope("t1", "p1", 2), "A-1")
    assert persisted is not None
    assert persisted.actual_start == datetime.fromisoformat(actual_start)
    assert persisted.duration_value == Decimal("12.50")
    assert persisted.duration_type is ActivityDurationType.FIXED_UNITS
    assert persisted.leveling_priority is ActivityLevelingPriority.HIGH
    assert persisted.original_duration == 15
    assert persisted.name == "Foundation Slab"
    assert persisted.short_name == "CP-A1"
    assert persisted.activity_type.value == "Resource Dependent"
    assert persisted.status.value == "In Progress"
    assert persisted.status_code.value == "Active"
    assert persisted.wbs_id == "W-ROOT"
    fresh_connection.close()

    status, loaded = _request(app, "GET", path + "/A-1")
    assert status == "200 OK"
    assert loaded["activity"]["actual_start"] == actual_start
    assert loaded["activity"]["wbs_id"] == "W-ROOT"
    status, listed = _request(app, "GET", path)
    assert status == "200 OK"
    assert [item["activity"]["activity_id"] for item in listed["activities"]] == ["A-1"]

    update_payload = {
        **create_payload,
        "planned_finish": "2026-10-24",
        "leveling_priority": "Lowest",
        "name": "Foundation Slab Complete",
        "short_name": "CP-A1B",
        "activity_type": "Task Dependent",
        "status": "Completed",
        "status_code": "Inactive",
        "duration_type": "Fixed Duration & Units/Time",
        "expected_revision": 1,
    }
    status, updated = _request(app, "PATCH", path + "/A-1", update_payload)
    assert status == "200 OK"
    assert updated["activity"]["record_revision"] == 2
    assert updated["activity"]["planned_finish"] == "2026-10-24"
    assert updated["activity"]["leveling_priority"] == "Lowest"
    assert updated["activity"]["name"] == "Foundation Slab Complete"
    assert updated["activity"]["short_name"] == "CP-A1B"
    assert updated["activity"]["activity_type"] == "Task Dependent"
    assert updated["activity"]["status"] == "Completed"
    assert updated["activity"]["status_code"] == "Inactive"
    assert updated["activity"]["duration_type"] == "Fixed Duration & Units/Time"

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
    assert partial["activity"]["duration_type"] == "Fixed Duration & Units/Time"
    assert partial["activity"]["actual_start"] == actual_start
    assert partial["activity"]["expected_finish"] == "2026-10-21"
    assert partial["activity"]["remaining_duration"] == 8
    assert partial["activity"]["percent_complete"] == 35.5
    assert partial["activity"]["percent_complete_type"] == "DURATION"
    assert partial["activity"]["leveling_priority"] == "Lowest"
    assert partial["activity"]["original_duration"] == 15
    assert partial["activity"]["name"] == "Foundation Slab Complete"
    assert partial["activity"]["short_name"] == "CP-A1B"
    assert partial["activity"]["activity_type"] == "Task Dependent"
    assert partial["activity"]["status"] == "Completed"
    assert partial["activity"]["status_code"] == "Inactive"

    # Explicit null clears an optional value; omission above preserved it.
    clear_payload = {
        "contract_version": "p6-activity-master-api.v1",
        "expected_revision": 3,
        "expected_finish": None,
        "short_name": None,
    }
    status, cleared = _request(app, "PATCH", path + "/A-1", clear_payload)
    assert status == "200 OK"
    assert cleared["activity"]["record_revision"] == 4
    assert cleared["activity"]["expected_finish"] is None
    assert cleared["activity"]["short_name"] is None
    assert cleared["activity"]["planned_finish"] == "2026-10-25"
    assert cleared["activity"]["original_duration"] == 15

    status, conflict = _request(
        app, "PATCH", path + "/A-1", {**update_payload, "expected_revision": 1}
    )
    assert status == "409 Conflict"
    assert conflict["code"] == "REVISION_CONFLICT"

    blank_name_payload = {
        "contract_version": "p6-activity-master-api.v1",
        "expected_revision": 4,
        "short_name": "   ",
    }
    status, blank = _request(app, "PATCH", path + "/A-1", blank_name_payload)
    assert status == "400 Bad Request"
    assert blank["code"] == "INVALID_SHORT_NAME"
    assert app_get_short_name(app) is None

    connection.close()


def app_get_short_name(app) -> str | None:
    status, loaded = _request(app, "GET", "/api/projects/p1/p6/activities/A-1")
    assert status == "200 OK"
    return loaded["activity"]["short_name"]


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
    assert error["code"] == "AUTHORIZATION_PERMISSION_DENIED"
    connection.close()



def test_authenticated_wbs_routes_preserve_parent_identity_and_revision():
    app, _repository, connection = _app()
    path = "/api/projects/p1/p6/wbs"
    root_status, root_response = _request(
        app,
        "POST",
        path,
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "wbs_id": "W-ROOT",
            "parent_kind": "project",
            "parent_wbs_id": None,
            "code": "1",
            "name": "Project Root",
            "sequence_number": 0,
        },
    )
    assert root_status == "201 Created"
    assert root_response["wbs"]["parent_kind"] == "project"
    assert root_response["wbs"]["parent_wbs_id"] is None
    assert root_response["wbs"]["record_revision"] == 1

    child_status, child_response = _request(
        app,
        "POST",
        path,
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "wbs_id": "W-CHILD",
            "parent_kind": "wbs",
            "parent_wbs_id": "W-ROOT",
            "code": "2",
            "name": "Concrete",
            "sequence_number": 10,
        },
    )
    assert child_status == "201 Created"
    assert child_response["wbs"]["parent_wbs_id"] == "W-ROOT"

    list_status, listed = _request(app, "GET", path)
    assert list_status == "200 OK"
    assert [item["wbs"]["wbs_id"] for item in listed["wbs_nodes"]] == ["W-ROOT", "W-CHILD"]

    patch_status, updated = _request(
        app,
        "PATCH",
        path + "/W-CHILD",
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "expected_revision": 1,
            "name": "Concrete Works",
        },
    )
    assert patch_status == "200 OK"
    assert updated["wbs"]["record_revision"] == 2
    assert updated["wbs"]["name"] == "Concrete Works"
    assert updated["wbs"]["parent_wbs_id"] == "W-ROOT"

    stale_status, _ = _request(
        app,
        "PATCH",
        path + "/W-CHILD",
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "expected_revision": 1,
            "name": "Stale write",
        },
    )
    assert stale_status == "409 Conflict"
    connection.close()



def test_authenticated_activity_create_requires_existing_wbs_assignment():
    app, _repository, connection = _app()
    wbs_status, _ = _request(
        app,
        "POST",
        "/api/projects/p1/p6/wbs",
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "wbs_id": "W-ROOT",
            "parent_kind": "project",
            "parent_wbs_id": None,
            "code": "1",
            "name": "Project Root",
            "sequence_number": 0,
        },
    )
    assert wbs_status == "201 Created"
    status, response = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "A-NO-WBS",
            "name": "Unassigned Activity",
            "duration_value": "1",
            "duration_unit": "working-day",
        },
    )
    assert status == "400 Bad Request"
    assert response["code"] == "WBS_REQUIRED"
    connection.close()


def test_authenticated_wbs_delete_rejects_stale_revision_and_assigned_activity():
    app, _repository, connection = _app()
    wbs_path = "/api/projects/p1/p6/wbs"
    root_status, root_response = _request(
        app,
        "POST",
        wbs_path,
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "wbs_id": "W-ROOT",
            "parent_kind": "project",
            "parent_wbs_id": None,
            "code": "1",
            "name": "Project Root",
            "sequence_number": 0,
        },
    )
    assert root_status == "201 Created"
    activity_status, activity_response = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "A-1",
            "name": "Assigned Activity",
            "duration_value": "1",
            "duration_unit": "working-day",
            "wbs_id": "W-ROOT",
        },
    )
    assert activity_status == "201 Created"
    assert activity_response["activity"]["wbs_id"] == "W-ROOT"

    stale_status, stale_response = _request(
        app,
        "DELETE",
        wbs_path + "/W-ROOT",
        {"contract_version": P6_WBS_MASTER_API_VERSION, "expected_revision": 2},
    )
    assert stale_status == "409 Conflict"
    assert stale_response["code"] == "REVISION_CONFLICT"

    in_use_status, in_use_response = _request(
        app,
        "DELETE",
        wbs_path + "/W-ROOT",
        {"contract_version": P6_WBS_MASTER_API_VERSION, "expected_revision": 1},
    )
    assert in_use_status == "409 Conflict"
    assert in_use_response["code"] == "WBS_IN_USE"
    connection.close()


def test_wbs_status_and_weighted_milestones_round_trip_through_http_routes(tmp_path):
    db_path = str(tmp_path / "cubi-wbs-milestones.sqlite")
    app, _activity_repository, connection = _app(db_path=db_path)
    base = "/api/projects/p1/p6/wbs"
    status, created = _request(app, "POST", base, {
        "contract_version": P6_WBS_MASTER_API_VERSION,
        "wbs_id": "W-ROOT",
        "parent_kind": "project",
        "parent_wbs_id": None,
        "code": "1",
        "name": "Project Root",
        "sequence_number": 0,
    })
    assert status == "201 Created"
    assert created["wbs"]["status"] == "planned"
    assert created["wbs"]["percent_complete_technique"] == "activities"
    assert created["wbs"]["percent_complete"] is None
    assert created["milestones"] == []

    status, updated = _request(app, "PATCH", base + "/W-ROOT", {
        "expected_revision": 1,
        "parent_kind": "project",
        "parent_wbs_id": None,
        "code": "1",
        "name": "Project Root",
        "sequence_number": 0,
        "status": "active",
        "percent_complete_technique": "milestones",
    })
    assert status == "200 OK"
    assert updated["wbs"]["status"] == "active"
    assert updated["wbs"]["percent_complete_technique"] == "milestones"
    assert updated["wbs"]["record_revision"] == 2

    milestones = [
        {"milestone_id": "M-1", "name": "Mobilize", "weight": 9, "completed": True, "sequence_number": 0},
        {"milestone_id": "M-2", "name": "Foundations", "weight": 1, "completed": False, "sequence_number": 1},
        {"milestone_id": "M-3", "name": "Steel", "weight": 1, "completed": False, "sequence_number": 2},
        {"milestone_id": "M-4", "name": "Handover", "weight": 1, "completed": False, "sequence_number": 3},
    ]
    status, saved = _request(app, "PUT", base + "/W-ROOT/milestones", {
        "expected_revision": 2,
        "milestones": milestones,
    })
    assert status == "200 OK"
    assert saved["wbs"]["record_revision"] == 3
    assert saved["wbs"]["percent_complete"] == 75.0
    assert [item["milestone_id"] for item in saved["milestones"]] == ["M-1", "M-2", "M-3", "M-4"]

    status, loaded = _request(app, "GET", base + "/W-ROOT/milestones")
    assert status == "200 OK"
    assert loaded["kind"] == "p6_wbs_milestones"
    assert loaded["record_revision"] == 3
    assert loaded["percent_complete_technique"] == "milestones"
    assert loaded["percent_complete"] == 75.0
    first = loaded["milestones"][0]
    assert {
        "milestone_id": first["milestone_id"],
        "name": first["name"],
        "weight": first["weight"],
        "completed": first["completed"],
        "sequence_number": first["sequence_number"],
    } == {
        "milestone_id": "M-1", "name": "Mobilize", "weight": 9.0, "completed": True, "sequence_number": 0,
    }
    assert first["record_revision"] == 1

    status, conflict = _request(app, "PUT", base + "/W-ROOT/milestones", {
        "expected_revision": 2,
        "milestones": milestones,
    })
    assert status == "409 Conflict"
    assert conflict["code"] == "REVISION_CONFLICT"

    status, invalid = _request(app, "PUT", base + "/W-ROOT/milestones", {
        "expected_revision": 3,
        "milestones": [{"milestone_id": "M-1", "name": "Mobilize", "weight": 0, "completed": False}],
    })
    assert status == "400 Bad Request"

    status, missing = _request(app, "GET", base + "/W-MISSING/milestones")
    assert status == "404 Not Found"

    connection.close()
    fresh = sqlite3.connect(db_path)
    fresh_repository = SQLiteWBSMasterRepository(fresh)
    persisted = fresh_repository.get(BackendScope("t1", "p1", 2), "W-ROOT")
    assert persisted is not None
    assert persisted.status.value == "active"
    assert persisted.percent_complete_technique.value == "milestones"
    assert [item.milestone_id for item in fresh_repository.list_milestones(BackendScope("t1", "p1", 2), "W-ROOT")] == [
        "M-1", "M-2", "M-3", "M-4"
    ]
    fresh.close()


def test_wbs_milestone_write_requires_project_write_permission(tmp_path):
    db_path = str(tmp_path / "cubi-wbs-milestone-permission.sqlite")
    app, _activity_repository, connection = _app(role="viewer", db_path=db_path)
    base = "/api/projects/p1/p6/wbs"
    # A project administrator seeded the hierarchy and milestones in the same database.
    admin, _admin_repository, admin_connection = _app(role="project_admin", db_path=db_path)
    status, created = _request(admin, "POST", base, {
        "contract_version": P6_WBS_MASTER_API_VERSION,
        "wbs_id": "W-ROOT",
        "parent_kind": "project",
        "parent_wbs_id": None,
        "code": "1",
        "name": "Project Root",
        "sequence_number": 0,
    })
    assert status == "201 Created"
    status, _ = _request(admin, "PUT", base + "/W-ROOT/milestones", {
        "expected_revision": created["wbs"]["record_revision"],
        "milestones": [{"milestone_id": "M-1", "name": "Start", "weight": 1, "completed": True}],
    })
    assert status == "200 OK"

    # The viewer session can read the same workspace record but cannot replace
    # the milestone list.
    status, loaded = _request(app, "GET", base + "/W-ROOT/milestones")
    assert status == "200 OK"
    assert [item["milestone_id"] for item in loaded["milestones"]] == ["M-1"]
    status, denied = _request(app, "PUT", base + "/W-ROOT/milestones", {
        "expected_revision": loaded["record_revision"],
        "milestones": [{"milestone_id": "M-2", "name": "Overwrite", "weight": 1, "completed": False}],
    })
    assert status == "403 Forbidden"
    assert denied["code"] == "AUTHORIZATION_PERMISSION_DENIED"
    connection.close()
    admin_connection.close()


def _seed_wbs_copy_hierarchy(app, base: str) -> None:
    for payload in (
        {
            "wbs_id": "W-ROOT",
            "parent_kind": "project",
            "parent_wbs_id": None,
            "code": "1",
            "name": "Project Root",
            "sequence_number": 0,
        },
        {
            "wbs_id": "W-CIVIL",
            "parent_kind": "wbs",
            "parent_wbs_id": "W-ROOT",
            "code": "1.1",
            "name": "Civil",
            "sequence_number": 0,
        },
        {
            "wbs_id": "W-CIVIL-SITE",
            "parent_kind": "wbs",
            "parent_wbs_id": "W-CIVIL",
            "code": "1.1.1",
            "name": "Site works",
            "sequence_number": 0,
        },
        {
            "wbs_id": "W-PM",
            "parent_kind": "wbs",
            "parent_wbs_id": "W-ROOT",
            "code": "1.2",
            "name": "Project management",
            "sequence_number": 1,
        },
    ):
        status, _ = _request(app, "POST", base, {"contract_version": P6_WBS_MASTER_API_VERSION, **payload})
        assert status == "201 Created"


def test_wbs_copy_route_creates_a_new_subtree_and_preserves_the_source():
    app, _repository, connection = _app()
    base = "/api/projects/p1/p6/wbs"
    _seed_wbs_copy_hierarchy(app, base)
    status, _ = _request(app, "PATCH", base + "/W-CIVIL", {
        "expected_revision": 1,
        "percent_complete_technique": "milestones",
    })
    assert status == "200 OK"
    status, _ = _request(app, "PUT", base + "/W-CIVIL/milestones", {
        "expected_revision": 2,
        "milestones": [
            {"milestone_id": "M-1", "name": "Design", "weight": 9, "completed": True},
            {"milestone_id": "M-2", "name": "Permits", "weight": 3, "completed": False},
        ],
    })
    assert status == "200 OK"

    status, copied = _request(app, "POST", base + "/W-CIVIL/copy", {
        "contract_version": P6_WBS_MASTER_API_VERSION,
        "expected_revision": 3,
        "target_parent_wbs_id": "W-PM",
        "code": "1.2.1",
    })
    assert status == "201 Created"
    assert copied["kind"] == "p6_wbs_copy"
    assert copied["source_wbs_id"] == "W-CIVIL"
    assert copied["target_parent_wbs_id"] == "W-PM"
    assert copied["root_wbs_id"].startswith("WBS-COPY-")
    assert [node["wbs"]["code"] for node in copied["wbs_nodes"]] == ["1.2.1", "1.1.1"]
    copy_root = copied["wbs_nodes"][0]["wbs"]
    assert copy_root["parent_wbs_id"] == "W-PM"
    assert copy_root["record_revision"] == 1
    assert copy_root["percent_complete"] == 75.0
    assert [item["milestone_id"] for item in copied["wbs_nodes"][0]["milestones"]] == ["M-1", "M-2"]

    status, listed = _request(app, "GET", base)
    assert status == "200 OK"
    assert len(listed["wbs_nodes"]) == 6
    source = next(node for node in listed["wbs_nodes"] if node["wbs"]["wbs_id"] == "W-CIVIL")
    assert source["wbs"]["record_revision"] == 3

    status, stale = _request(app, "POST", base + "/W-CIVIL/copy", {
        "expected_revision": 1,
        "target_parent_wbs_id": "W-PM",
        "code": "1.2.3",
    })
    assert status == "409 Conflict"
    assert stale["code"] == "REVISION_CONFLICT"

    status, conflict = _request(app, "POST", base + "/W-CIVIL/copy", {
        "expected_revision": 3,
        "target_parent_wbs_id": "W-PM",
        "code": "1.2.1",
    })
    assert status == "400 Bad Request"
    assert conflict["code"] == "WBS_SIBLING_CODE_CONFLICT"

    status, missing = _request(app, "POST", base + "/W-MISSING/copy", {
        "expected_revision": 1,
        "target_parent_wbs_id": "W-PM",
        "code": "1.2.4",
    })
    assert status == "404 Not Found"
    status, missing_target = _request(app, "POST", base + "/W-CIVIL/copy", {
        "expected_revision": 3,
        "target_parent_wbs_id": "W-NOWHERE",
        "code": "1.2.4",
    })
    assert status == "400 Bad Request"
    assert missing_target["code"] == "WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH"
    connection.close()


def test_wbs_copy_route_requires_project_write_permission(tmp_path):
    db_path = str(tmp_path / "cubi-wbs-copy-permission.sqlite")
    app, _repository, connection = _app(role="viewer", db_path=db_path)
    base = "/api/projects/p1/p6/wbs"
    admin, _admin_repository, admin_connection = _app(role="project_admin", db_path=db_path)
    _seed_wbs_copy_hierarchy(admin, base)

    status, listed = _request(app, "GET", base)
    assert status == "200 OK"
    source = next(node for node in listed["wbs_nodes"] if node["wbs"]["wbs_id"] == "W-CIVIL")

    status, denied = _request(app, "POST", base + "/W-CIVIL/copy", {
        "expected_revision": source["wbs"]["record_revision"],
        "target_parent_wbs_id": "W-PM",
        "code": "1.2.1",
    })
    assert status == "403 Forbidden"
    assert denied["code"] == "AUTHORIZATION_PERMISSION_DENIED"

    status, after = _request(app, "GET", base)
    assert len(after["wbs_nodes"]) == 4
    connection.close()
    admin_connection.close()


def test_activity_create_inherits_project_defaults_and_explicit_values_win(tmp_path):
    db_path = str(tmp_path / "cubi-activity-defaults.sqlite")
    app, _repository, connection = _app(
        db_path=db_path,
        default_activity_type="Level of Effort",
        default_percent_complete_type="PHYSICAL",
        default_duration_type="Fixed Units",
    )
    try:
        status, _ = _request(
            app,
            "POST",
            "/api/projects/p1/p6/wbs",
            {
                "contract_version": P6_WBS_MASTER_API_VERSION,
                "wbs_id": "W-ROOT",
                "parent_kind": "project",
                "parent_wbs_id": None,
                "code": "1",
                "name": "Project Root",
                "sequence_number": 0,
            },
        )
        assert status == "201 Created"
        path = "/api/projects/p1/p6/activities"
        inherited = {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": "A-DEFAULT",
            "name": "Inherits defaults",
            "duration_value": "5",
            "duration_unit": "working-day",
            "wbs_id": "W-ROOT",
        }
        status, created = _request(app, "POST", path, inherited)
        assert status == "201 Created"
        assert created["activity"]["activity_type"] == "Level of Effort"
        assert created["activity"]["percent_complete_type"] == "PHYSICAL"
        assert created["activity"]["duration_type"] == "Fixed Units"

        # The server records exactly which defaults were applied to the new
        # activity; the client never supplies this history.
        status, history = _request(app, "GET", "/api/projects/p1/defaults-history")
        assert status == "200 OK"
        assert history["contract_version"] == "project-defaults-history-api.v1"
        assert [event["activity_id"] for event in history["events"]] == ["A-DEFAULT"]
        event = history["events"][0]
        assert event["event_id"] == "p1@A-DEFAULT"
        assert event["applied_activity_type"] == "Level of Effort"
        assert event["applied_percent_complete_type"] == "PHYSICAL"
        assert event["applied_duration_type"] == "Fixed Units"
        assert event["applied_cost_account_id"] == ""
        assert event["actor_user_id"] == "u1"

        explicit = {
            **inherited,
            "activity_id": "A-EXPLICIT",
            "activity_type": "Start Milestone",
            "percent_complete_type": "SCOPE",
            "duration_type": "Fixed Units/Time",
        }
        status, created = _request(app, "POST", path, explicit)
        assert status == "201 Created"
        assert created["activity"]["activity_type"] == "Start Milestone"
        assert created["activity"]["percent_complete_type"] == "SCOPE"
        assert created["activity"]["duration_type"] == "Fixed Units/Time"

        # A request that supplies every default writes no application row:
        # the defaults contributed nothing.
        status, history = _request(app, "GET", "/api/projects/p1/defaults-history")
        assert status == "200 OK"
        assert [event["activity_id"] for event in history["events"]] == ["A-DEFAULT"]

        # Changing a default afterwards never rewrites the stored activities:
        # each activity keeps the independent value it was created with.
        projects_status, project = _request(app, "GET", "/api/projects/p1")
        assert projects_status == "200 OK"
        assert project["project"]["default_duration_type"] == "Fixed Units"

        # Changing the project default afterwards never rewrites stored
        # activities: each keeps the value it was created with.
        status, patched = _request(
            app,
            "PATCH",
            "/api/projects/p1",
            {
                "name": "Project One",
                "default_duration_type": "Fixed Duration & Units",
                "expected_revision": 0,
            },
        )
        assert status == "200 OK"
        assert patched["project"]["default_duration_type"] == "Fixed Duration & Units"
        status, reloaded = _request(app, "GET", path + "/A-DEFAULT")
        assert status == "200 OK"
        assert reloaded["activity"]["duration_type"] == "Fixed Units"

        # V26 supports exactly four Duration Type values; an unknown label is
        # rejected instead of silently falling back to a default.
        status, error = _request(
            app,
            "POST",
            path,
            {**inherited, "activity_id": "A-BAD", "duration_type": "Fixed Effort"},
        )
        assert status == "400 Bad Request"
        assert error["code"] == "P6_ACTIVITY_MASTER_REQUEST_INVALID"
    finally:
        connection.close()


def test_activity_cost_account_inherits_the_project_default_and_can_change_per_activity(tmp_path):
    db_path = str(tmp_path / "cubi-activity-cost-account.sqlite")
    app, _repository, connection = _app(
        db_path=db_path,
        default_cost_account_id="CA-CIVIL",
        cost_accounts=CostAccounts({"CA-CIVIL", "CA-MEP"}),
    )
    try:
        status, _ = _request(
            app,
            "POST",
            "/api/projects/p1/p6/wbs",
            {
                "contract_version": P6_WBS_MASTER_API_VERSION,
                "wbs_id": "W-ROOT",
                "parent_kind": "project",
                "parent_wbs_id": None,
                "code": "1",
                "name": "Project Root",
                "sequence_number": 0,
            },
        )
        assert status == "201 Created"
        path = "/api/projects/p1/p6/activities"
        base = {
            "contract_version": "p6-activity-master-api.v1",
            "duration_value": "5",
            "duration_unit": "working-day",
            "wbs_id": "W-ROOT",
        }
        status, created = _request(
            app, "POST", path, {**base, "activity_id": "A-DEFAULT", "name": "Inherits"}
        )
        assert status == "201 Created"
        assert created["activity"]["cost_account_id"] == "CA-CIVIL"

        status, history = _request(app, "GET", "/api/projects/p1/defaults-history")
        assert status == "200 OK"
        assert history["events"][0]["applied_cost_account_id"] == "CA-CIVIL"
        assert history["events"][0]["actor_user_id"] == "u1"

        status, created = _request(
            app,
            "POST",
            path,
            {
                **base,
                "activity_id": "A-EXPLICIT",
                "name": "Explicit account",
                "cost_account_id": "CA-MEP",
            },
        )
        assert status == "201 Created"
        assert created["activity"]["cost_account_id"] == "CA-MEP"

        status, patched = _request(
            app,
            "PATCH",
            path + "/A-DEFAULT",
            {
                "contract_version": "p6-activity-master-api.v1",
                "expected_revision": 1,
                "cost_account_id": "CA-MEP",
            },
        )
        assert status == "200 OK"
        assert patched["activity"]["cost_account_id"] == "CA-MEP"

        # A default change never rewrites existing activities.
        status, changed = _request(
            app,
            "PATCH",
            "/api/projects/p1",
            {
                "name": "Project One",
                "default_cost_account_id": "CA-MEP",
                "expected_revision": 0,
            },
        )
        assert status == "200 OK"
        assert changed["project"]["default_cost_account_id"] == "CA-MEP"
        status, reloaded = _request(app, "GET", path + "/A-EXPLICIT")
        assert status == "200 OK"
        assert reloaded["activity"]["cost_account_id"] == "CA-MEP"

        status, cleared = _request(
            app,
            "PATCH",
            path + "/A-DEFAULT",
            {
                "contract_version": "p6-activity-master-api.v1",
                "expected_revision": 2,
                "cost_account_id": None,
            },
        )
        assert status == "200 OK"
        assert cleared["activity"]["cost_account_id"] is None

        status, error = _request(
            app,
            "POST",
            path,
            {
                **base,
                "activity_id": "A-UNKNOWN",
                "name": "Unknown account",
                "cost_account_id": "CA-MISSING",
            },
        )
        assert status == "400 Bad Request"
        assert error["code"] == "P6_ACTIVITY_COST_ACCOUNT_NOT_FOUND"
    finally:
        connection.close()


def test_checkout_holder_blocks_activity_and_wbs_writes_with_409(tmp_path):
    db_path = str(tmp_path / "cubi-checkout-http.sqlite")
    app, _repository, _connection = _app(db_path=db_path, checkout_holder="u-other")

    status, body = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "activity_id": "A-1",
            "duration_value": "2",
            "duration_unit": "working-day",
        },
    )
    assert status == "409 Conflict"
    assert body["code"] == "PROJECT_CHECKED_OUT_BY_OTHER"

    status, body = _request(
        app,
        "POST",
        "/api/projects/p1/p6/wbs",
        {
            "wbs_id": "W-1",
            "parent_kind": "project",
            "code": "W-1",
            "name": "Civil",
        },
    )
    assert status == "409 Conflict"
    assert body["code"] == "PROJECT_CHECKED_OUT_BY_OTHER"


def test_wbs_responsible_obs_route_is_revision_guarded_and_authenticated():
    app, _repository, connection = _app()
    created, _ = _request(
        app, "POST", "/api/projects/p1/p6/wbs",
        {
            "contract_version": P6_WBS_MASTER_API_VERSION,
            "wbs_id": "W-RESP",
            "parent_kind": "project",
            "parent_wbs_id": None,
            "code": "1",
            "name": "Responsibility WBS",
            "sequence_number": 0,
        },
    )
    assert created.startswith("201")

    updated, body = _request(
        app, "PUT", "/api/projects/p1/p6/wbs/W-RESP/responsibility",
        {"responsible_obs_id": "OBS-OPERATIONS", "expected_revision": 0},
    )
    assert updated.startswith("200")
    assert body["responsible_obs_id"] == "OBS-OPERATIONS"
    assert body["revision"] == 1

    read, body = _request(
        app, "GET", "/api/projects/p1/p6/wbs/W-RESP/responsibility"
    )
    assert read.startswith("200")
    assert body["responsible_obs_id"] == "OBS-OPERATIONS"

    stale, body = _request(
        app, "PUT", "/api/projects/p1/p6/wbs/W-RESP/responsibility",
        {"responsible_obs_id": "OBS-OPERATIONS", "expected_revision": 0},
    )
    assert stale.startswith("409")
    assert body["code"] == "P6_WBS_RESPONSIBILITY_REVISION_CONFLICT"
    connection.close()

