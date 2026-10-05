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
from construction_pm.p6_baseline_api import P6BaselineAPI, P6_BASELINE_API_VERSION
from construction_pm.p6_financial_period_api import P6FinancialPeriodAPI, P6_FINANCIAL_PERIOD_API_VERSION
from construction_pm.p6_mapping_api import P6MappingAPI, P6_MAPPING_API_VERSION
from construction_pm.p6_interchange_api import P6InterchangeAPI, P6_INTERCHANGE_API_VERSION
from construction_pm.p6_mapping_registry import P6MappingFormat
from construction_pm.p6_xer_codec import P6XerCodec
from construction_pm.p6_mapping_registry import P6MappingRegistryApplicationService, SQLiteP6MappingRegistryRepository
from construction_pm.dependency_graph_api import DependencyGraphAPI
from construction_pm.p6_financial_period_repository import P6FinancialPeriodApplicationService, SQLiteP6FinancialPeriodRepository
from construction_pm.p6_baseline_repository import P6BaselineApplicationService, SQLiteP6BaselineRepository
from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint
from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
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


class SyncHandler:
    def __init__(self):
        self.calls = []

    def handle(self, mutation):
        self.calls.append(mutation)


def sync_routes():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    handler = SyncHandler()
    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("t1", "p1", handler))
    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        sync_endpoint_factory=lambda _tenant, _project: endpoint,
    )
    return routes, handler


def test_authenticated_sync_mutation_uses_project_context_and_idempotency_header():
    r, handler = sync_routes()
    body = {
        "contract_version": "sync-mutation.v1",
        "mutation_id": "m1",
        "tenant_id": "t1",
        "project_id": "p1",
        "expected_revision": 2,
        "operation": "update_activity",
        "payload": {"activity_id": "A-1"},
        "idempotency_key": "idem-1",
    }
    status, _, raw = r.handle(
        "POST", "/api/v1/sync/mutations", cookies={"cp_session": "s1"},
        headers={"Idempotency-Key": "idem-1"}, body=json.dumps(body).encode(),
    )
    assert status == 200
    result = json.loads(raw)
    assert result["contract_version"] == "sync-outcome.v1"
    assert result["disposition"] == "acknowledged"
    assert handler.calls[0].project_id == "p1"


def test_authenticated_sync_rejects_missing_idempotency_header_and_cross_scope():
    r, _ = sync_routes()
    body = {
        "contract_version": "sync-mutation.v1", "mutation_id": "m1",
        "tenant_id": "t1", "project_id": "p1", "expected_revision": 2,
        "operation": "update_activity", "payload": {}, "idempotency_key": "idem-1",
    }
    status, _, raw = r.handle("POST", "/api/v1/sync/mutations", cookies={"cp_session": "s1"}, body=json.dumps(body).encode())
    assert status == 400
    assert json.loads(raw)["code"] == "SYNC_REQUEST_INVALID"

    status, _, raw = r.handle("POST", "/api/v1/sync/mutations", cookies={"cp_session": "s1"}, headers={"Idempotency-Key": "idem-1"}, body=json.dumps({**body, "project_id": "p2"}).encode())
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_authenticated_sync_rejects_spoofed_tenant_and_stale_revision():
    r, _ = sync_routes()
    body = {
        "contract_version": "sync-mutation.v1", "mutation_id": "m1",
        "tenant_id": "spoofed", "project_id": "p1", "expected_revision": 2,
        "operation": "update_activity", "payload": {}, "idempotency_key": "idem-1",
    }
    status, _, raw = r.handle("POST", "/api/v1/sync/mutations", cookies={"cp_session": "s1"}, headers={"Idempotency-Key": "idem-1"}, body=json.dumps(body).encode())
    assert status == 200
    assert json.loads(raw)["error_code"] == "INVALID_PROJECT_CONTEXT"

    body["tenant_id"] = "t1"
    body["expected_revision"] = 1
    status, _, raw = r.handle("POST", "/api/v1/sync/mutations", cookies={"cp_session": "s1"}, headers={"Idempotency-Key": "idem-1"}, body=json.dumps(body).encode())
    assert status == 200
    result = json.loads(raw)
    assert result["disposition"] == "conflict"
    assert result["error_code"] == "STALE_REVISION"


def test_authenticated_sync_revision_endpoint_returns_authoritative_context():
    r, _ = sync_routes()
    status, _, raw = r.handle("GET", "/api/v1/sync/revision/p1", cookies={"cp_session": "s1"})
    assert status == 200
    result = json.loads(raw)
    assert result == {
        "contract_version": "sync-project-revision.v1",
        "tenant_id": "t1", "project_id": "p1", "revision": 2,
    }

    status, _, raw = r.handle("GET", "/api/v1/sync/revision/p2", cookies={"cp_session": "s1"})
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_authenticated_sync_routes_require_session():
    r, _ = sync_routes()
    status, _, raw = r.handle("GET", "/api/v1/sync/revision/p1")
    assert status == 401
    assert json.loads(raw)["code"] == "SESSION_REQUIRED"

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


def p6_routes(roles=frozenset({"project_admin"})):
    import sqlite3
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", roles, now + timedelta(hours=1))
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
    baseline_api = P6BaselineAPI(
        P6BaselineApplicationService(SQLiteP6BaselineRepository(connection), transaction_manager),
        default_project_policy(),
    )
    financial_period_api = P6FinancialPeriodAPI(
        P6FinancialPeriodApplicationService(SQLiteP6FinancialPeriodRepository(connection), transaction_manager),
        default_project_policy(),
    )
    mapping_service = P6MappingRegistryApplicationService(SQLiteP6MappingRegistryRepository(connection), transaction_manager)
    mapping_api = P6MappingAPI(mapping_service, default_project_policy())
    interchange_api = P6InterchangeAPI(
        mapping_service,
        default_project_policy(),
        {P6MappingFormat.XER_PROJECT: P6XerCodec()},
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_field_registry_api=field_api,
        p6_layout_definition_api=layout_api,
        p6_formula_authority_api=formula_api,
        p6_calendar_read_api=calendar_api,
        p6_baseline_api=baseline_api,
        p6_financial_period_api=financial_period_api,
        p6_mapping_api=mapping_api,
        p6_interchange_api=interchange_api,
    ), field_api, layout_api


def test_p6_mapping_http_routes_create_get_and_list_preserve_contract():
    r, _, _ = p6_routes()
    payload = {
        "mapping_id": "MAP-1",
        "registry_version": "p6-field-registry.v1",
        "format": "XER_PROJECT",
        "subject_area": "Activity",
        "source_field": "task_code",
        "canonical_field": "activity.activity_id",
        "status": "SUPPORTED",
        "source_type": "TEXT",
        "canonical_type": "TEXT",
        "unit": None,
        "notes": "Project activity code mapping",
    }
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/mappings", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode()
    )
    assert status == 200
    saved = json.loads(body)
    assert saved["contract_version"] == P6_MAPPING_API_VERSION
    assert saved["mapping"]["mapping_id"] == "MAP-1"
    assert saved["mapping"]["format"] == "XER_PROJECT"

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/mappings/MAP-1", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body) == saved

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/mappings", cookies={"cp_session": "s1"}
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == P6_MAPPING_API_VERSION
    assert [item["mapping"]["mapping_id"] for item in payload["mappings"]] == ["MAP-1"]


def test_p6_mapping_http_routes_require_scope_and_permission():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET", "/api/projects/p2/p6/mappings", cookies={"cp_session": "s1"}
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    r, _, _ = p6_routes(roles=frozenset())
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/mappings", cookies={"cp_session": "s1"}
    )
    assert status == 403
    assert "authorization" in json.loads(body)["code"].lower()


def test_p6_mapping_http_get_returns_not_found_and_rejects_malformed_payload():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/mappings/missing", cookies={"cp_session": "s1"}
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_MAPPING_NOT_FOUND"

    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/mappings", cookies={"cp_session": "s1"}, body=b'{"format":"NOT_A_FORMAT"}'
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_MAPPING_REQUEST_INVALID"


def test_p6_registry_http_routes_preserve_versioned_api_contract_envelope():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 1)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
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
    assert payload["contract_version"] == "p6-layout-definition-api.v1"
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
    assert saved["contract_version"] == "p6-layout-definition-api.v1"
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
    payload = json.loads(body)
    assert payload["contract_version"] == "p6-field-registry-api.v1"
    expected_udf = {key: value for key, value in saved.items() if key != "contract_version"}
    assert payload["udfs"] == [expected_udf]


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


def test_p6_financial_period_http_routes_create_get_and_list_preserve_contract():
    r, _, _ = p6_routes()
    payload = {
        "period_id": "2026-09",
        "name": "September 2026",
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "status": "OPEN",
    }
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/financial-periods", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode()
    )
    assert status == 200
    saved = json.loads(body)
    assert saved["contract_version"] == P6_FINANCIAL_PERIOD_API_VERSION
    assert saved["financial_period"]["period_id"] == "2026-09"

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/financial-periods/2026-09", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body) == saved

    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/financial-periods", cookies={"cp_session": "s1"}
    )
    assert status == 200
    listed = json.loads(body)
    assert listed["contract_version"] == P6_FINANCIAL_PERIOD_API_VERSION
    assert [item["financial_period"]["period_id"] for item in listed["financial_periods"]] == ["2026-09"]


def test_p6_financial_period_routes_reject_cross_scope_missing_permission_and_invalid_payload():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET", "/api/projects/p2/p6/financial-periods", cookies={"cp_session": "s1"}
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    r, _, _ = p6_routes(roles=frozenset({"writer"}))
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/financial-periods", cookies={"cp_session": "s1"}
    )
    assert status == 403
    assert json.loads(body)["code"] == "authorization denied for permission=project.read"

    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/financial-periods", cookies={"cp_session": "s1"}, body=b"{\"period_id\": 7}"
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_FINANCIAL_PERIOD_REQUEST_INVALID"


def test_p6_financial_period_get_returns_not_found():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/financial-periods/missing", cookies={"cp_session": "s1"}
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_FINANCIAL_PERIOD_NOT_FOUND"


def test_p6_baseline_http_routes_create_get_and_list_preserve_contract():
    r, _, _ = p6_routes()
    payload = {
        "baseline_id": "BL-1",
        "name": "Primary Baseline",
        "baseline_type": "PRIMARY",
        "source_revision": 2,
        "created_at": "2026-10-05T00:00:00+00:00",
        "notes": "Release baseline",
    }
    status, _, body = r.handle("POST", "/api/projects/p1/p6/baselines", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    assert status == 200
    saved = json.loads(body)
    assert saved["contract_version"] == P6_BASELINE_API_VERSION
    assert saved["baseline"]["source_revision"] == 2
    assert saved["baseline"]["baseline_type"] == "PRIMARY"

    status, _, body = r.handle("GET", "/api/projects/p1/p6/baselines/BL-1", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body) == saved

    status, _, body = r.handle("GET", "/api/projects/p1/p6/baselines", cookies={"cp_session": "s1"})
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == P6_BASELINE_API_VERSION
    assert [item["baseline"]["baseline_id"] for item in payload["baselines"]] == ["BL-1"]


def test_p6_baseline_routes_reject_cross_scope_and_missing_permission():
    r, _, _ = p6_routes()
    status, _, body = r.handle("GET", "/api/projects/p2/p6/baselines", cookies={"cp_session": "s1"})
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    r, _, _ = p6_routes(roles=frozenset())
    status, _, body = r.handle("GET", "/api/projects/p1/p6/baselines", cookies={"cp_session": "s1"})
    assert status == 403
    assert "authorization" in json.loads(body)["code"].lower()


def test_p6_baseline_get_returns_not_found():
    r, _, _ = p6_routes()
    status, _, body = r.handle("GET", "/api/projects/p1/p6/baselines/missing", cookies={"cp_session": "s1"})
    assert status == 404
    assert json.loads(body)["code"] == "P6_BASELINE_NOT_FOUND"


def test_p6_baseline_create_rejects_malformed_payload():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/baselines", cookies={"cp_session": "s1"}, body=json.dumps({
            "baseline_id": "BL-1",
            "name": "Bad",
            "baseline_type": "NOT_VALID",
            "source_revision": 2,
            "created_at": "2026-10-05T00:00:00+00:00",
        }).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_BASELINE_REQUEST_INVALID"


class _DependencyGraphReadAPI:
    def __init__(self, result):
        self.result = result

    def get(self, *, tenant_id, project_id, resource_id, auth_context):
        assert tenant_id == "t1"
        assert project_id == "p1"
        assert auth_context.project_id == "p1"
        return self.result


def dependency_routes(*, roles=frozenset({"project_admin"}), result=None):
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", roles, now + timedelta(hours=1))
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        dependency_graph_api=_DependencyGraphReadAPI(result),
    )


def test_dependency_graph_http_read_preserves_versioned_contract_and_project_context():
    r = dependency_routes(result={
        "contract_version": "dependency-graph.v1",
        "operation": "get",
        "resource_id": "schedule:link-1",
        "tenant_id": "t1",
        "project_id": "p1",
        "revision": 2,
        "graph_revision": 3,
        "source_resource_id": "schedule:task-a",
        "target_resource_id": "schedule:task-b",
        "source_revision": 1,
        "target_revision": 2,
        "dependency_type": "depends_on",
        "metadata": {"origin": "p6"},
    })
    status, _, body = r.handle(
        "GET", "/api/projects/p1/dependencies/schedule:link-1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == "dependency-graph.v1"
    assert payload["resource_id"] == "schedule:link-1"
    assert payload["project_id"] == "p1"
    assert payload["graph_revision"] == 3


def test_dependency_graph_http_read_requires_session_and_project_scope():
    r = dependency_routes(result={})
    status, _, body = r.handle(
        "GET", "/api/projects/p1/dependencies/schedule:link-1"
    )
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"

    status, _, body = r.handle(
        "GET", "/api/projects/p2/dependencies/schedule:link-1",
        cookies={"cp_session": "s1"},
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_dependency_graph_http_read_returns_not_found():
    r = dependency_routes(result=None)
    status, _, body = r.handle(
        "GET", "/api/projects/p1/dependencies/schedule:missing",
        cookies={"cp_session": "s1"},
    )
    assert status == 404
    assert json.loads(body)["code"] == "DEPENDENCY_NOT_FOUND"


def test_dependency_graph_http_read_rejects_malformed_resource_path():
    r = dependency_routes(result={})
    status, _, body = r.handle(
        "GET", "/api/projects/p1/dependencies/",
        cookies={"cp_session": "s1"},
    )
    assert status == 400
    assert json.loads(body)["code"] == "DEPENDENCY_REQUEST_INVALID"


def test_p6_interchange_http_import_export_preserves_versioned_contract_and_scope():
    r, _, _ = p6_routes()
    mapping_payload = {
        "mapping_id": "MAP-INTERCHANGE-1",
        "registry_version": "p6-field-registry.v1",
        "format": "XER_PROJECT",
        "subject_area": "Activity",
        "source_field": "task_code",
        "canonical_field": "activity.activity_id",
        "status": "SUPPORTED",
        "source_type": "TEXT",
        "canonical_type": "TEXT",
        "unit": None,
        "notes": "HTTP interchange test",
    }
    status, _, _ = r.handle(
        "POST", "/api/projects/p1/p6/mappings", cookies={"cp_session": "s1"}, body=json.dumps(mapping_payload).encode()
    )
    assert status == 200

    xer = b"%T\tTASK\n%F\ttask_code\n%R\tA-100\n%E\n"
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/interchange/XER_PROJECT/import",
        cookies={"cp_session": "s1"}, body=xer,
    )
    assert status == 200
    imported = json.loads(body)
    assert imported["contract_version"] == P6_INTERCHANGE_API_VERSION
    assert imported["format"] == "XER_PROJECT"
    assert imported["rows"][0]["values"]["activity.activity_id"] == "A-100"

    export_body = json.dumps({"values": [{"activity.activity_id": "A-100"}], "extensions": [{"p6.xer.table": "TASK"}]}).encode()
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/interchange/XER_PROJECT/export",
        cookies={"cp_session": "s1"}, body=export_body,
    )
    assert status == 200
    exported = json.loads(body)
    assert exported["contract_version"] == P6_INTERCHANGE_API_VERSION
    assert exported["document"]["encoding"] == "utf-8"
    assert "%R\\tA-100" in exported["document"]["data"]


def test_p6_interchange_http_requires_scope_and_permission():
    r, _, _ = p6_routes(roles=frozenset({"viewer"}))
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/interchange/XER_PROJECT/import",
        cookies={"cp_session": "s1"}, body=b"%T\\tTASK\\n%F\\ttask_code\\n%R\\tA-100\\n%E\\n",
    )
    assert status == 403
    assert "permission=project.write" in json.loads(body)["code"]

    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST", "/api/projects/p2/p6/interchange/XER_PROJECT/import",
        cookies={"cp_session": "s1"}, body=b"%T\\tTASK\\n%F\\ttask_code\\n%R\\tA-100\\n%E\\n",
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
