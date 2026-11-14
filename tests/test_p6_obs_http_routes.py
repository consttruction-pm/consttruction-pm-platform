import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_obs_api import P6OBSNodeAPI
from construction_pm.p6_obs_repository import P6OBSApplicationService, SQLiteP6OBSRepository


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self):
        self.items = {"p1": ProjectSummary("p1", "t1", "Project One", 2)}

    def list_for_user(self, tenant_id, user_id):
        return tuple(self.items.values())

    def get_for_user(self, tenant_id, project_id, user_id):
        return self.items.get(project_id)

    def create_for_user(self, tenant_id, user_id, project_id, name, *, obs_id="", **_):
        project = ProjectSummary(project_id, tenant_id, name, 0, obs_id=obs_id)
        self.items[project_id] = project
        return project

    def update_for_user(
        self,
        tenant_id,
        user_id,
        project_id,
        *,
        expected_revision,
        name,
        obs_id=None,
        **_,
    ):
        current = self.items.get(project_id)
        if current is None or current.settings_revision != expected_revision:
            return None
        updated = ProjectSummary(
            project_id,
            tenant_id,
            name,
            current.revision,
            settings_revision=current.settings_revision + 1,
            obs_id=current.obs_id if obs_id is None else obs_id,
        )
        self.items[project_id] = updated
        return updated


def routes(roles=frozenset({"planner"})):
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset(roles), now + timedelta(hours=1)
    )
    obs_repository = SQLiteP6OBSRepository(sqlite3.connect(":memory:"))
    service = ProjectLifecycleService(
        Sessions(session),
        Projects(),
        default_project_policy(),
        obs_nodes=obs_repository,
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_obs_node_api=P6OBSNodeAPI(
            P6OBSApplicationService(obs_repository), default_project_policy()
        ),
    )


def post_node(router, **payload):
    return router.handle(
        "POST",
        "/api/projects/p1/p6/obs-nodes",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode(),
    )


def test_obs_node_http_writes_and_reads_the_enterprise_hierarchy():
    router = routes()
    status, _, body = post_node(
        router, obs_id="OBS-ROOT", code="ROOT", name="Company", sequence_number=1
    )
    assert status == 200, body
    assert json.loads(body)["obs_node"]["name"] == "Company"

    status, _, body = post_node(
        router, obs_id="OBS-CIVIL", parent_obs_id="OBS-ROOT", name="Civil"
    )
    assert status == 200, body

    status, _, body = router.handle(
        "GET", "/api/projects/p1/p6/obs-nodes", cookies={"cp_session": "s1"}
    )
    assert status == 200
    listed = json.loads(body)
    assert listed["contract_version"] == "p6-obs-node-api.v1"
    assert [entry["obs_id"] for entry in listed["obs_nodes"]] == [
        "OBS-CIVIL",
        "OBS-ROOT",
    ]

    status, _, body = router.handle(
        "GET", "/api/projects/p1/p6/obs-nodes/OBS-CIVIL", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body)["obs_node"]["parent_obs_id"] == "OBS-ROOT"

    status, _, body = router.handle(
        "GET", "/api/projects/p1/p6/obs-nodes/OBS-MISSING", cookies={"cp_session": "s1"}
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_OBS_NODE_NOT_FOUND"


def test_obs_node_reads_are_open_to_viewers_but_writes_are_not():
    router = routes(roles={"viewer"})
    status, _, body = post_node(router, obs_id="OBS-ROOT", name="Company")
    assert status == 403
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"

    status, _, body = router.handle(
        "GET", "/api/projects/p1/p6/obs-nodes", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body)["obs_nodes"] == []


def test_obs_node_http_rejects_missing_parents_and_cycles():
    router = routes()
    status, _, body = post_node(
        router, obs_id="OBS-CHILD", parent_obs_id="OBS-MISSING", name="Child"
    )
    assert status == 400
    assert json.loads(body)["code"] == "OBS_PARENT_NOT_FOUND"

    assert post_node(router, obs_id="OBS-A", name="A")[0] == 200
    assert post_node(router, obs_id="OBS-B", parent_obs_id="OBS-A", name="B")[0] == 200

    status, _, body = post_node(
        router, obs_id="OBS-A", parent_obs_id="OBS-B", name="A"
    )
    assert status == 400
    assert json.loads(body)["code"] == "OBS_PARENT_CYCLE"

    status, _, body = post_node(
        router, obs_id="OBS-SELF", parent_obs_id="OBS-SELF", name="Self"
    )
    assert status == 400
    assert json.loads(body)["code"] == "OBS_SELF_PARENT"


def test_obs_node_http_rejects_a_malformed_node():
    router = routes()
    status, _, body = post_node(router, obs_id="OBS-ROOT", name="")
    assert status == 400
    assert json.loads(body)["code"] == "P6_OBS_NODE_REQUEST_INVALID"


def test_project_patch_assigns_and_clears_the_responsibility_structure_node():
    router = routes(roles={"project_admin"})
    assert post_node(router, obs_id="OBS-CIVIL", name="Civil")[0] == 200

    status, _, body = router.handle(
        "PATCH",
        "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Project One", "obs_id": "OBS-CIVIL", "expected_revision": 0}).encode(),
    )
    assert status == 200, body
    assert json.loads(body)["project"]["obs_id"] == "OBS-CIVIL"

    status, _, body = router.handle(
        "GET", "/api/projects/p1", cookies={"cp_session": "s1"}
    )
    assert json.loads(body)["project"]["obs_id"] == "OBS-CIVIL"

    status, _, body = router.handle(
        "PATCH",
        "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Project One", "obs_id": "", "expected_revision": 1}).encode(),
    )
    assert status == 200, body
    assert json.loads(body)["project"]["obs_id"] == ""


def test_project_patch_rejects_an_unknown_responsibility_structure_node():
    router = routes(roles={"project_admin"})
    status, _, body = router.handle(
        "PATCH",
        "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Project One", "obs_id": "OBS-UNKNOWN", "expected_revision": 0}).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "PROJECT_OBS_NODE_NOT_FOUND"
