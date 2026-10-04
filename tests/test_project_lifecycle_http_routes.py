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
from construction_pm.p6_formula_authority_api import P6FormulaAuthorityAPI
from construction_pm.p6_formula_authority_api import P6_FORMULA_AUTHORITY_API_VERSION
from construction_pm.calendar_master_repository import CalendarMaster, SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI, P6_CALENDAR_READ_API_VERSION
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_periods import CalendarTimePeriodFactors
from construction_pm.scheduling.calendar_system import CalendarSystem
from datetime import date
from decimal import Decimal
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
    formula_api = P6FormulaAuthorityAPI(field_api.field_service, default_project_policy())
    calendar_repository = SQLiteCalendarMasterRepository(connection)
    snapshot_repository = SQLiteCalendarSnapshotRepository(connection)
    calendar_api = P6CalendarReadAPI(calendar_repository, snapshot_repository, default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_field_registry_api=field_api,
        p6_layout_definition_api=layout_api,
        p6_formula_authority_api=formula_api,
        p6_calendar_read_api=calendar_api,
    ), field_api, layout_api


def test_p6_registry_http_routes_preserve_versioned_api_contract_envelope():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 1)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project.read", "project.write"}))
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.activity_id"), auth_context=auth)
    status, _, body = r.handle("GET", "/api/projects/p1/p6/fields/p6-field-registry.v1", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["contract_version"] == "p6-field-registry-api.v1"

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


def test_p6_calendar_route_returns_authoritative_catalog():
    r, _, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    CalendarMaster(scope, "CAL-1", "1", "working-day", "Project Calendar")
    calendar = CalendarMaster(scope, "CAL-1", "1", "working-day", "Project Calendar")
    r._p6_calendar_read_api.calendar_repository.save(calendar)

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/calendars", cookies={"cp_session": "s1"}
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == P6_CALENDAR_READ_API_VERSION
    assert payload["scope"]["project_id"] == "p1"
    assert payload["calendars"][0]["calendar_id"] == "CAL-1"
    assert payload["calendars"][0]["kind"] == "working-day"


def test_p6_calendar_snapshot_route_returns_canonical_shared_core_snapshot():
    r, _, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    calendar = CalendarMaster(scope, "CAL-1", "1", "working-day", "Project Calendar")
    r._p6_calendar_read_api.calendar_repository.save(calendar)
    working_calendar = WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({date(2026, 3, 21)}),
        system=CalendarSystem.JALALI,
        time_period_factors=CalendarTimePeriodFactors(
            hours_per_day=Decimal("8"), hours_per_week=Decimal("40"),
            hours_per_month=Decimal("176"), hours_per_year=Decimal("2080"),
        ),
    )
    r._p6_calendar_read_api.snapshot_repository.save(calendar, working_calendar)

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/calendars/CAL-1/1/snapshot", cookies={"cp_session": "s1"}
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == P6_CALENDAR_READ_API_VERSION
    assert payload["calendar"]["calendar_version"] == "1"
    assert payload["snapshot"]["time_period_factors"]["hours_per_day"] == "8"


def test_p6_calendar_routes_require_session_and_reject_cross_scope():
    r, _, _ = p6_routes()
    status, _, body = r.handle("GET", "/api/projects/p1/p6/calendars")
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"

    status, _, body = r.handle(
        "GET", "/api/projects/p2/p6/calendars", cookies={"cp_session": "s1"}
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_p6_formula_route_exposes_authoritative_versioned_validation():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.percent_complete"), auth_context=auth)
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formulas/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expression": "[activity.percent_complete] + 1"}).encode("utf-8"),
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == P6_FORMULA_AUTHORITY_API_VERSION
    assert payload["validation"]["valid"] is True
    assert payload["dependencies"]["field_ids"] == ["activity.percent_complete"]
    assert payload["result_type"]["data_type"] == "double"


def test_p6_formula_route_requires_session_and_rejects_invalid_request():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formulas/p6-field-registry.v1",
        body=b"{}",
    )
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"

    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formulas/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expression": 123}).encode("utf-8"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_FORMULA_REQUEST_INVALID"


def test_p6_formula_route_preserves_structured_shared_core_validation_error():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formulas/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expression": "[missing.field] + 1"}).encode("utf-8"),
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == P6_FORMULA_AUTHORITY_API_VERSION
    assert payload["validation"]["valid"] is False
    assert payload["validation"]["error_code"]


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

def test_p6_udf_http_routes_preserve_versioned_api_contract_envelope():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"udf_id":"activity.status","subject_area":"Activity","display_name":"Status","data_type":"string"}).encode(),
    )
    assert status == 200
    assert json.loads(body)["contract_version"] == "p6-field-registry-api.v1"

def test_p6_udf_write_route_persists_authenticated_definition():
    r, _, _ = p6_routes()
    payload = {
        "udf_id": "activity.status",
        "subject_area": "Activity",
        "display_name": "Status",
        "data_type": "enum",
        "writable": True,
        "nullable": False,
        "unit": None,
        "allowed_values": ["Planned", "In Progress", "Complete"],
    }
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode("utf-8"),
    )
    assert status == 200
    saved = json.loads(body)
    assert saved["udf_id"] == "activity.status"
    assert saved["allowed_values"] == payload["allowed_values"]

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    payload = json.loads(body)\n    assert payload["contract_version"] == "p6-field-registry-api.v1"\n    expected_udf = {key: value for key, value in saved.items() if key != "contract_version"}\n    assert payload["udfs"] == [expected_udf]


def test_p6_udf_write_route_rejects_invalid_payload():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "udf_id": "activity.status",
            "subject_area": "Activity",
            "display_name": "Status",
            "data_type": "not-a-real-type",
        }).encode("utf-8"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_UDF_REQUEST_INVALID"


def test_p6_udf_write_route_requires_session_cookie():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        body=b"{}",
    )
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


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


def test_p6_field_write_route_persists_authenticated_field():
    r, _, _ = p6_routes()
    payload = {
        "field_id": "activity.custom_flag",
        "subject_area": "Activity",
        "p6_field": "CustomFlag",
        "display_name": "Custom Flag",
        "data_type": "boolean",
        "writable": True,
        "computed": False,
        "unit": None,
        "disposition": "implemented",
    }
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/fields/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode("utf-8"),
    )
    assert status == 200
    saved = json.loads(body)
    assert saved["field_id"] == "activity.custom_flag"
    assert saved["data_type"] == "boolean"

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/fields/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert any(item["field_id"] == "activity.custom_flag" for item in json.loads(body)["fields"])


def test_p6_field_write_route_rejects_non_object_json():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/fields/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=b"[]",
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_FIELD_REQUEST_INVALID"


def test_p6_field_write_route_requires_session_cookie():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/fields/p6-field-registry.v1",
        body=b"{}",
    )
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"
