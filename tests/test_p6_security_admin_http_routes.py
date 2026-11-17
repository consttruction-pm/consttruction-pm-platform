import json
import sqlite3
from datetime import datetime, timezone

from construction_pm.application.authorization import AuthorizationContext
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_associated_resource_api import P6AssociatedResourceAPI
from construction_pm.p6_associated_resource_repository import SQLiteP6AssociatedResourceRepository
from construction_pm.p6_obs_repository import P6OBSNode, P6OBSApplicationService, SQLiteP6OBSRepository
from construction_pm.p6_project_security_api import P6ProjectSecurityAPI
from construction_pm.p6_project_security_repository import SQLiteP6ProjectSecurityRepository
from construction_pm.p6_resource_master_repository import P6Resource, SQLiteP6ResourceRepository


class Session:
    tenant_id = "tenant-a"
    user_id = "admin-user"
    roles = frozenset({"admin"})


class Lifecycle:
    def get_session(self, session_id, *, now):
        assert session_id == "session"
        return Session()


class AdminPolicy:
    def allows_global_privilege(self, context, code):
        return code in {"add_edit_delete_users", "add_edit_delete_security_profiles"}


def test_tenant_admin_routes_create_project_profile_assign_obs_and_associated_resource():
    connection = sqlite3.connect(":memory:")
    obs = SQLiteP6OBSRepository(connection)
    P6OBSApplicationService(obs).save(P6OBSNode("tenant-a", "OBS-ROOT", name="Root"))
    projects = {"project-a": "OBS-ROOT"}
    project_security_repository = SQLiteP6ProjectSecurityRepository(
        connection,
        project_obs_lookup=lambda tenant, project: projects.get(project),
        obs_repository=obs, user_exists=lambda tenant, user: tenant == "tenant-a",
    )
    project_security_api = P6ProjectSecurityAPI(project_security_repository, AdminPolicy())

    resource_repository = SQLiteP6ResourceRepository(connection)
    resource_repository.save(P6Resource("tenant-a", "project-a", 1, "R-1", "Crew"))
    associated_repository = SQLiteP6AssociatedResourceRepository(
        connection, user_exists=lambda tenant, user: (tenant, user) == ("tenant-a", "user-1")
    )
    associated_api = P6AssociatedResourceAPI(associated_repository, AdminPolicy())

    routes = object.__new__(ProjectLifecycleHttpRoutes)
    routes._api = Lifecycle()
    routes._p6_project_security_api = project_security_api
    routes._p6_associated_resource_api = associated_api
    now = datetime.now(timezone.utc)

    status, _, body = routes._handle_p6_security_admin_route(
        "POST", "/api/admin/p6/project-security-profiles", session_id="session",
        now=now, body=json.dumps({
            "profile_id": "profile-pm", "name": "Project Manager",
            "privileges": ["add_edit_activities_except_relationships"],
        }).encode(),
    )
    assert status == 200
    assert json.loads(body)["profile"]["profile_id"] == "profile-pm"

    status, _, body = routes._handle_p6_security_admin_route(
        "POST", "/api/admin/p6/project-security-profiles/obs-grants",
        session_id="session", now=now,
        body=json.dumps({"user_id": "user-1", "obs_id": "OBS-ROOT", "profile_id": "profile-pm"}).encode(),
    )
    assert status == 200
    assert json.loads(body)["grant"]["obs_id"] == "OBS-ROOT"

    status, _, body = routes._handle_p6_security_admin_route(
        "PUT", "/api/admin/p6/users/user-1/associated-resource",
        session_id="session", now=now, body=json.dumps({"resource_id": "R-1"}).encode(),
    )
    assert status == 200
    assert json.loads(body)["association"]["resource_id"] == "R-1"

    status, _, body = routes._handle_p6_security_admin_route(
        "GET", "/api/admin/p6/users/user-1/associated-resource",
        session_id="session", now=now, body=b"",
    )
    assert status == 200
    assert json.loads(body)["association"]["resource_id"] == "R-1"
