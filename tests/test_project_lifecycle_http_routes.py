from datetime import datetime, timedelta, timezone
import json

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_field_registry import (
    P6_FIELD_REGISTRY_REFERENCE_PRODUCT,
    P6_FIELD_REGISTRY_REFERENCE_VERSION,
    P6_FIELD_REGISTRY_STATUS,
    get_field,
)
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    SQLiteP6FieldRegistryRepository,
)
from construction_pm.p6_layout_definition_api import P6LayoutDefinitionAPI
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    SQLiteP6LayoutRepository,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    SQLiteP6UserDefinedFieldRepository,
)


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self): self.items = {"p1": ("p1", "Project One", 2)}

    def list_for_user(self, tenant_id, user_id):
        return tuple(
            ProjectSummary(pid, tenant_id, name, rev)
            for pid, (pid, name, rev) in self.items.items()
        )

    def get_for_user(self, tenant_id, project_id, user_id):
        item = self.items.get(project_id)
        if not item: return None
        return ProjectSummary(item[0], tenant_id, item[1], item[2])

    def create_for_user(self, tenant_id, user_id, project_id, name):
        self.items[project_id] = (project_id, name, 0)
        return ProjectSummary(project_id, tenant_id, name, 0)


def routes():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
    )


def test_requires_session_cookie():
    status, _, _ = routes().handle("GET", "/api/session")
    assert status == 401


def test_session_and_project_routes_bridge_application_to_web_contract():
    r = routes()
    status, _, body = r.handle("GET", "/api/session", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["tenant_id"] == "t1"

    status, _, body = r.handle("GET", "/api/projects", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["projects"][0]["project_id"] == "p1"

    status, _, body = r.handle(
        "POST", "/api/projects/p1/open", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body)["context"]["project_id"] == "p1"


def test_browser_cannot_supply_identity_headers_as_authority():
    r = routes()
    status, _, _ = r.handle("GET", "/api/projects", cookies={"cp_session": "missing"})
    assert status == 401


def p6_routes():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    import sqlite3
    connection = sqlite3.connect(":memory:")
    field_api = P6FieldRegistryAPI(
        field_service=P6FieldRegistryApplicationService(
            SQLiteP6FieldRegistryRepository(connection), SQLiteTransactionManager(connection)
        ),
        udf_service=P6UserDefinedFieldApplicationService(
            SQLiteP6UserDefinedFieldRepository(connection), SQLiteTransactionManager(connection)
        ),
        authorization_policy=default_project_policy(),
    )
    layout_api = P6LayoutDefinitionAPI(
        SQLiteP6LayoutRepository(connection), default_project_policy()
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_field_registry_api=field_api,
        p6_layout_definition_api=layout_api,
    ), field_api, layout_api


def test_p6_field_registry_route_returns_authorized_activity_fields():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    from construction_pm.application.authorization import AuthorizationContext
    auth_context = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_id"), auth_context=auth_context)
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_name"), auth_context=auth_context)

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/fields/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["registry_version"] == "p6-field-registry.v1"
    assert payload["reference_product"] == P6_FIELD_REGISTRY_REFERENCE_PRODUCT
    assert payload["reference_version"] == P6_FIELD_REGISTRY_REFERENCE_VERSION
    assert payload["status"] == P6_FIELD_REGISTRY_STATUS
    assert [item["field_id"] for item in payload["fields"]] == [
        "activity.activity_id",
        "activity.activity_name",
    ]


def test_p6_layout_route_returns_persisted_layout():
    r, _, layout_api = p6_routes()
    layout_api.repository.upsert(
        PersistedP6Layout(
            BackendScope("t1", "p1", 2),
            "project",
            "activity",
            1,
            (LayoutColumn("activity_id", True, 0, None, 120, "start", False, False),),
            {"density": "compact"},
        )
    )

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/activity",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["schema_version"] == "p6-layout.v1"
    assert payload["scope"] == "project"
    assert payload["view_id"] == "activity"
    assert payload["metadata"] == {"density": "compact"}


def test_p6_layout_route_returns_not_found_for_missing_layout():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/missing",
        cookies={"cp_session": "s1"},
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_LAYOUT_NOT_FOUND"
