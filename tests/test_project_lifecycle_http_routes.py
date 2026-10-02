from datetime import datetime, timedelta, timezone
import json

from construction_pm.application.authorization import default_project_policy, AuthorizationContext
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import get_field, P6FieldType
from construction_pm.p6_field_registry_api import P6FieldRegistryAPI
from construction_pm.p6_field_registry_repository import P6FieldRegistryApplicationService, SQLiteP6FieldRegistryRepository
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    P6UserDefinedFieldDefinition,
    SQLiteP6UserDefinedFieldRepository,
)
from construction_pm.p6_layout_definition_api import P6LayoutDefinitionAPI
from construction_pm.p6_layout_definition_repository import LayoutColumn, PersistedP6Layout, SQLiteP6LayoutRepository


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
    import sqlite3
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    connection = sqlite3.connect(":memory:")
    transaction_manager = SQLiteTransactionManager(connection)
    field_api = P6FieldRegistryAPI(
        P6FieldRegistryApplicationService(SQLiteP6FieldRegistryRepository(connection), transaction_manager),
        P6UserDefinedFieldApplicationService(SQLiteP6UserDefinedFieldRepository(connection), transaction_manager),
        default_project_policy(),
    )
    layout_api = P6LayoutDefinitionAPI(SQLiteP6LayoutRepository(connection), default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_field_registry_api=field_api,
        p6_layout_definition_api=layout_api,
    ), field_api, layout_api


def test_p6_registry_route_requires_session_cookie():
    r, _, _ = p6_routes()
    status, _, body = r.handle("GET", "/api/projects/p1/p6/fields/p6-field-registry.v1")
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


def test_p6_registry_route_returns_authorized_activity_fields():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_id"), auth_context=auth)
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_name"), auth_context=auth)
    status, _, body = r.handle("GET", "/api/projects/p1/p6/fields/p6-field-registry.v1", cookies={"cp_session": "s1"})
    assert status == 200
    payload = json.loads(body)
    assert payload["registry_version"] == "p6-field-registry.v1"
    assert [item["field_id"] for item in payload["fields"]] == ["activity.activity_id", "activity.activity_name"]


def test_p6_routes_reject_cross_scope_project_context():
    r, _, _ = p6_routes()
    status, _, body = r.handle("GET", "/api/projects/p2/p6/fields/p6-field-registry.v1", cookies={"cp_session": "s1"})
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_p6_layout_route_returns_persisted_layout():
    r, _, layout_api = p6_routes()
    layout_api.repository.upsert(PersistedP6Layout(
        BackendScope("t1", "p1", 2), "project", "activity", 1,
        (LayoutColumn("activity_id", True, 0, None, 120, "start", False, False),),
        {"density": "compact"},
    ))
    status, _, body = r.handle("GET", "/api/projects/p1/p6/layouts/project/activity", cookies={"cp_session": "s1"})
    assert status == 200
    payload = json.loads(body)
    assert payload["schema_version"] == "p6-layout.v1"
    assert payload["scope"] == "project"
    assert payload["view_id"] == "activity"
    assert payload["metadata"] == {"density": "compact"}


def test_p6_layout_write_route_persists_authenticated_layout():
    r, _, _ = p6_routes()
    payload = {
        "revision": 1,
        "columns": [{
            "field_id": "activity_id",
            "visible": True,
            "order": 0,
            "label": None,
            "width": 120.0,
            "alignment": "start",
            "pinned": False,
            "frozen": False,
        }],
        "metadata": {"density": "compact"},
    }
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/layouts/project/activity",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode("utf-8"),
    )
    assert status == 200
    saved = json.loads(body)
    assert saved["schema_version"] == "p6-layout.v1"
    assert saved["scope"] == "project"
    assert saved["view_id"] == "activity"
    assert saved["metadata"] == {"density": "compact"}

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/activity",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(body) == saved


def test_p6_layout_write_route_rejects_non_object_json():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/layouts/project/activity",
        cookies={"cp_session": "s1"},
        body=b"[]",
    )
    assert status == 400
    assert json.loads(body)["code"] == "INVALID_LAYOUT_REQUEST"


def test_p6_layout_write_route_rejects_non_list_columns():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/layouts/project/activity",
        cookies={"cp_session": "s1"},
        body=json.dumps({"columns": {}}).encode("utf-8"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "INVALID_LAYOUT_COLUMNS"


def test_p6_layout_write_route_requires_session_cookie():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/layouts/project/activity",
        body=b"{}",
    )
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


def test_p6_layout_route_returns_not_found_for_missing_layout():
    r, _, _ = p6_routes()
    status, _, body = r.handle("GET", "/api/projects/p1/p6/layouts/project/missing", cookies={"cp_session": "s1"})
    assert status == 404
    assert json.loads(body)["code"] == "P6_LAYOUT_NOT_FOUND"

def test_p6_udf_route_requires_session_cookie():
    r, _, _ = p6_routes()
    status, _, body = r.handle("GET", "/api/projects/p1/p6/udfs/p6-field-registry.v1")
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


def test_p6_udf_route_returns_authoritative_allowed_values():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    field_api.save_udf(
        P6UserDefinedFieldDefinition(
            scope=scope,
            registry_version="p6-field-registry.v1",
            udf_id="activity.status",
            subject_area="Activity",
            display_name="Status",
            data_type=P6FieldType.ENUM,
            writable=True,
            nullable=False,
            unit=None,
            allowed_values=("Planned", "In Progress", "Complete"),
        ),
        auth_context=auth,
    )
    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["registry_version"] == "p6-field-registry.v1"
    assert payload["udfs"] == [{
        "udf_id": "activity.status",
        "subject_area": "Activity",
        "display_name": "Status",
        "data_type": "enum",
        "writable": True,
        "nullable": False,
        "unit": None,
        "allowed_values": ["Planned", "In Progress", "Complete"],
    }]


def test_p6_udf_route_rejects_cross_scope_project_context():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET",
        "/api/projects/p2/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
