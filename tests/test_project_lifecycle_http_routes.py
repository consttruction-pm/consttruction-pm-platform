from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import json

from construction_pm.application.authorization import default_project_policy, AuthorizationContext
from construction_pm.change_claim_api import ChangeClaimAPI, P0_CHANGE_CLAIM_API_VERSION
from construction_pm.change_claims import ChangeClaimService, InMemoryChangeClaimRepository
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import (
    ProjectLifecycleHttpRoutes,
    _stable_error_code,
)
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
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
from construction_pm.p6_udf_value_api import P6UserDefinedFieldValueAPI
from construction_pm.p6_user_defined_field_values_repository import (
    P6UserDefinedFieldValueApplicationService,
    SQLiteP6UserDefinedFieldValueRepository,
)
from construction_pm.p6_layout_definition_api import P6LayoutDefinitionAPI
from construction_pm.p6_formula_authority_api import P6FormulaAuthorityAPI
from construction_pm.p6_formula_authority_api import P6_FORMULA_AUTHORITY_API_VERSION
from construction_pm.p6_formula_column import P6FormulaColumnAPI, P6FormulaColumnService
from construction_pm.p6_formula_definition_repository import (
    P6FormulaDefinitionApplicationService,
    SQLiteP6FormulaDefinitionRepository,
)
from construction_pm.calendar_master_repository import CalendarMaster, SQLiteCalendarMasterRepository
from construction_pm.calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI, P6_CALENDAR_READ_API_VERSION
from construction_pm.p6_baseline_api import P6BaselineAPI, P6_BASELINE_API_VERSION
from construction_pm.p6_financial_period_api import P6FinancialPeriodAPI, P6_FINANCIAL_PERIOD_API_VERSION
from construction_pm.p6_mapping_api import P6MappingAPI, P6_MAPPING_API_VERSION
from construction_pm.p6_interchange_api import P6InterchangeAPI, P6_INTERCHANGE_API_VERSION
from construction_pm.p6_resource_read_api import P6ResourceReadAPI, P6_RESOURCE_READ_API_VERSION
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI, P6_RESOURCE_WRITE_API_VERSION
from construction_pm.p6_resource_assignment_repository import P6ResourceAssignment, P6ResourceAssignmentApplicationService, P6ResourceAssignmentPeriodApplicationService, P6ResourceAssignmentPeriodValue, SQLiteP6ResourceAssignmentRepository, SQLiteP6ResourceAssignmentPeriodRepository
from construction_pm.p6_resource_spread_api import P6ResourceSpreadAPI, P6_RESOURCE_SPREAD_API_VERSION
from construction_pm.p6_resource_spread_repository import P6ResourceSpreadApplicationService, SQLiteP6ResourceSpreadRepository
from construction_pm.p6_code_api import P6CodeAPI, P6_CODE_API_VERSION
from construction_pm.p6_code_repository import P6CodeApplicationService, P6CodeValue, SQLiteP6CodeRepository
from construction_pm.p6_mapping_registry import P6MappingFormat
from construction_pm.p6_xer_codec import P6XerCodec
from construction_pm.p6_mapping_registry import P6MappingRegistryApplicationService, SQLiteP6MappingRegistryRepository
from construction_pm.dependency_graph_api import DependencyGraphAPI
from construction_pm.p6_financial_period_repository import P6FinancialPeriodApplicationService, SQLiteP6FinancialPeriodRepository
from construction_pm.p6_baseline_repository import P6BaselineApplicationService, SQLiteP6BaselineRepository
from construction_pm.p6_relationship_api import P6RelationshipAPI, P6_RELATIONSHIP_API_VERSION
from construction_pm.relationship_master_repository import DurationUnit, SQLiteRelationshipMasterRepository
from construction_pm.client_sync.api_endpoint import VersionedSyncEndpoint
from construction_pm.client_sync.application_gateway import ApplicationSyncGateway
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_periods import CalendarTimePeriodFactors
from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate
from datetime import date
from decimal import Decimal
from construction_pm.p6_layout_definition_repository import LayoutColumn, PersistedP6Layout, SQLiteP6LayoutRepository


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self):
        self.items = {
            "p1": ProjectSummary("p1", "t1", "Project One", 2)
        }

    def list_for_user(self, tenant_id, user_id):
        return tuple(
            ProjectSummary(
                p.project_id, tenant_id, p.name, p.revision,
                description=p.description, start_date=p.start_date,
                date_system=p.date_system,
                primary_calendar_id=p.primary_calendar_id,
                settings_revision=p.settings_revision,
                business_domain=p.business_domain,
                obs_responsible_manager=p.obs_responsible_manager,
                website_url=p.website_url,
                checkout_state=p.checkout_state,
                checked_out_by=p.checked_out_by,
                checked_out_at=p.checked_out_at,
            )
            for p in self.items.values()
        )

    def get_for_user(self, tenant_id, project_id, user_id):
        project = self.items.get(project_id)
        if project is None: return None
        return ProjectSummary(
            project.project_id, tenant_id, project.name, project.revision,
            description=project.description, start_date=project.start_date,
            date_system=project.date_system,
            primary_calendar_id=project.primary_calendar_id,
            settings_revision=project.settings_revision,
            business_domain=project.business_domain,
            obs_responsible_manager=project.obs_responsible_manager,
            website_url=project.website_url,
            checkout_state=project.checkout_state,
            checked_out_by=project.checked_out_by,
            checked_out_at=project.checked_out_at,
        )

    def create_for_user(
        self, tenant_id, user_id, project_id, name, *,
        description="", start_date=None, date_system="gregorian",
        primary_calendar_id=None, business_domain="",
        obs_responsible_manager="", website_url="",
    ):
        project = ProjectSummary(
            project_id, tenant_id, name, 0,
            description=description, start_date=start_date,
            date_system=date_system, primary_calendar_id=primary_calendar_id,
            business_domain=business_domain,
            obs_responsible_manager=obs_responsible_manager,
            website_url=website_url,
        )
        self.items[project_id] = project
        return project

    def update_for_user(
        self, tenant_id, user_id, project_id, *, expected_revision, name,
        description="", start_date=None, date_system="gregorian",
        primary_calendar_id=None, business_domain=None,
        obs_responsible_manager=None, website_url=None,
    ):
        project = self.items.get(project_id)
        if project is None or project.settings_revision != expected_revision: return None
        updated = ProjectSummary(
            project_id, tenant_id, name, project.revision,
            description=description, start_date=start_date,
            date_system=date_system, primary_calendar_id=primary_calendar_id,
            settings_revision=project.settings_revision + 1,
            business_domain=(
                business_domain if business_domain is not None else project.business_domain
            ),
            obs_responsible_manager=(
                obs_responsible_manager
                if obs_responsible_manager is not None
                else project.obs_responsible_manager
            ),
            website_url=(
                website_url if website_url is not None else project.website_url
            ),
            checkout_state=project.checkout_state,
            checked_out_by=project.checked_out_by,
            checked_out_at=project.checked_out_at,
        )
        self.items[project_id] = updated
        return updated

    def set_checkout_for_user(
        self, tenant_id, user_id, project_id, *, checked_out,
        expected_revision, actor_user_id, changed_at,
    ):
        project = self.items.get(project_id)
        if project is None or project.settings_revision != expected_revision:
            return None
        if checked_out and project.checkout_state == "checked_out":
            return None
        if not checked_out and (
            project.checkout_state != "checked_out"
            or project.checked_out_by != actor_user_id
        ):
            return None
        updated = ProjectSummary(
            project_id, tenant_id, project.name, project.revision,
            description=project.description, start_date=project.start_date,
            date_system=project.date_system,
            primary_calendar_id=project.primary_calendar_id,
            settings_revision=project.settings_revision + 1,
            status=project.status, business_domain=project.business_domain,
            obs_responsible_manager=project.obs_responsible_manager,
            website_url=project.website_url,
            checkout_state="checked_out" if checked_out else "checked_in",
            checked_out_by=actor_user_id if checked_out else "",
            checked_out_at=changed_at.isoformat() if checked_out else None,
        )
        self.items[project_id] = updated
        return updated


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


class FakeP6CalendarAPI:
    def __init__(self):
        self.calls = []

    def create(self, scope, request, *, auth_context):
        self.calls.append(("create", scope, request, auth_context))
        return {"contract_version": "p6-calendar.v1", "calendar_id": request.calendar_id}

    def update(self, scope, request, *, auth_context):
        self.calls.append(("update", scope, request, auth_context))
        return {"contract_version": "p6-calendar.v1", "calendar_id": request.calendar_id}

    def delete(self, scope, calendar_id, calendar_version, *, expected_revision, auth_context):
        self.calls.append(("delete", scope, calendar_id, calendar_version, expected_revision, auth_context))
        return True

    def copy(self, scope, source_calendar_id, source_calendar_version, target_calendar_id, target_calendar_version, *, auth_context):
        self.calls.append(("copy", scope, source_calendar_id, source_calendar_version, target_calendar_id, target_calendar_version, auth_context))
        return {"contract_version": "p6-calendar.v1", "calendar_id": target_calendar_id}

    def replace(self, scope, target_calendar_id, target_calendar_version, source_calendar_id, source_calendar_version, *, auth_context):
        self.calls.append(("replace", scope, target_calendar_id, target_calendar_version, source_calendar_id, source_calendar_version, auth_context))
        return {"contract_version": "p6-calendar.v1", "calendar_id": target_calendar_id}

    def save_exception(self, exception, *, auth_context):
        self.calls.append(("save_exception", exception, auth_context))
        return exception.canonical_snapshot()

    def list_exceptions(self, scope, calendar_id, calendar_version, *, auth_context):
        self.calls.append(("list_exceptions", scope, calendar_id, calendar_version, auth_context))
        return ()

    def delete_exception(self, scope, calendar_id, calendar_version, exception_date, *, auth_context):
        self.calls.append(("delete_exception", scope, calendar_id, calendar_version, exception_date, auth_context))
        return True

    def revise_exception(self, scope, calendar_id, calendar_version, exception_date, *, mode, total_work_hours, intervals, expected_revision, auth_context):
        self.calls.append(("revise_exception", scope, calendar_id, calendar_version, exception_date, mode, total_work_hours, intervals, expected_revision, auth_context))
        return {
            "contract_version": "p6-calendar.v1",
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "date": exception_date.isoformat(),
            "mode": mode,
            "system": "gregorian",
            "total_work_hours": total_work_hours,
            "intervals": [],
            "record_revision": expected_revision + 1,
        }

    def save_work_hours(self, rule, *, auth_context):
        self.calls.append(("save_work_hours", rule, auth_context))
        return rule.canonical_snapshot()

    def replace_work_hours(self, rule, *, expected_revision, auth_context):
        self.calls.append(("replace_work_hours", rule, expected_revision, auth_context))
        return rule.canonical_snapshot()

    def list_work_hours(self, scope, calendar_id, calendar_version, kind, *, auth_context):
        self.calls.append(("list_work_hours", scope, calendar_id, calendar_version, kind, auth_context))
        return ()


def p6_calendar_write_routes():
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
    calendar_api = FakeP6CalendarAPI()
    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_calendar_api=calendar_api,
    )
    return routes, calendar_api


def test_p6_calendar_http_write_routes_use_authenticated_project_scope():
    r, api = p6_calendar_write_routes()
    payload = {
        "contract_version": "p6-calendar.v1",
        "calendar_id": "CAL-1",
        "calendar_version": "1",
        "calendar_type": "project",
        "kind": "working-time",
        "name": "Project Calendar",
        "expected_revision": 0,
    }
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/calendars",
        cookies={"cp_session": "s1"}, body=json.dumps(payload).encode()
    )
    assert status == 200
    assert json.loads(body)["calendar_id"] == "CAL-1"
    call = api.calls[-1]
    assert call[0] == "create"
    assert call[1] == BackendScope("t1", "p1", 2)
    assert call[3].tenant_id == "t1"
    assert call[3].project_id == "p1"

    status, _, body = r.handle(
        "PATCH", "/api/projects/p1/p6/calendars/CAL-1/1",
        cookies={"cp_session": "s1"},
        body=json.dumps({**payload, "name": "Renamed", "expected_revision": 1}).encode(),
    )
    assert status == 200
    assert api.calls[-1][0] == "update"

    status, _, body = r.handle(
        "DELETE", "/api/projects/p1/p6/calendars/CAL-1/1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 2}).encode(),
    )
    assert status == 200
    assert api.calls[-1][0] == "delete"


def test_p6_calendar_http_copy_replace_exception_and_work_hours_contracts():
    r, api = p6_calendar_write_routes()

    for operation in ("copy", "replace"):
        status, _, _ = r.handle(
            "POST", f"/api/projects/p1/p6/calendars/CAL-1/1/{operation}",
            cookies={"cp_session": "s1"},
            body=json.dumps({"target_calendar_id": "CAL-2", "target_calendar_version": "1"}).encode(),
        )
        assert status == 200
        assert api.calls[-1][0] == operation

    exception_payload = {
        "date": "2026-10-01",
        "mode": "nonwork",
        "system": "gregorian",
        "intervals": [],
    }
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/calendars/CAL-1/1/exceptions",
        cookies={"cp_session": "s1"}, body=json.dumps(exception_payload).encode(),
    )
    assert status == 200
    assert api.calls[-1][0] == "save_exception"
    assert json.loads(body)["mode"] == "nonwork"

    jalali_payload = {
        "date": "1405-01-01",
        "mode": "nonwork",
        "system": "jalali",
        "intervals": [],
    }
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/calendars/CAL-1/1/exceptions",
        cookies={"cp_session": "s1"}, body=json.dumps(jalali_payload).encode(),
    )
    assert status == 200
    jalali_result = json.loads(body)
    assert jalali_result["system"] == "jalali"
    assert jalali_result["date"] == JalaliDate(1405, 1, 1).to_gregorian().isoformat()
    assert api.calls[-1][0] == "save_exception"
    assert api.calls[-1][1].exception_date == JalaliDate(1405, 1, 1).to_gregorian()

    invalid_jalali_payload = {**jalali_payload, "date": "1405-13-01"}
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/calendars/CAL-1/1/exceptions",
        cookies={"cp_session": "s1"}, body=json.dumps(invalid_jalali_payload).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_CALENDAR_REQUEST_INVALID"

    work_hours_payload = {
        "kind": "standard_work_week",
        "weekday": 0,
        "is_working_day": True,
        "total_work_hours": "8",
        "intervals": [],
    }
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/calendars/CAL-1/1/work-hours",
        cookies={"cp_session": "s1"}, body=json.dumps(work_hours_payload).encode(),
    )
    assert status == 200
    assert api.calls[-1][0] == "save_work_hours"
    assert json.loads(body)["kind"] == "standard_work_week"

    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/calendars/CAL-1/1/work-hours",
        cookies={"cp_session": "s1"},
        body=json.dumps({**work_hours_payload, "replace": True, "expected_revision": 3}).encode(),
    )
    assert status == 200
    assert api.calls[-1][0] == "replace_work_hours"
    assert api.calls[-1][2] == 3

    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/calendars/CAL-1/1/work-hours",
        cookies={"cp_session": "s1"},
        body=json.dumps({**work_hours_payload, "replace": True}).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_CALENDAR_REQUEST_INVALID"

    # A browser GET carries no JSON body; the route must still return every
    # stored work-hour contract so the window can render the workweek.
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/calendars/CAL-1/1/work-hours",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(body)["work_hours"] == []
    listed_kinds = [call[4] for call in api.calls if call[0] == "list_work_hours"]
    assert listed_kinds[-4:] == [
        "standard_work_week", "standard_detailed_work_hours",
        "detailed_work_hours", "total_work_hours",
    ]

    status, _, body = r.handle(
        "DELETE", "/api/projects/p1/p6/calendars/CAL-1/1/exceptions/2026-10-01",
        cookies={"cp_session": "s1"}, body=b"{}",
    )
    assert status == 200
    assert json.loads(body)["deleted"] is True
    assert api.calls[-1][0] == "delete_exception"
    assert api.calls[-1][4] == date(2026, 10, 1)
    assert api.calls[-1][5].project_id == "p1"

    status, _, body = r.handle(
        "PUT", "/api/projects/p1/p6/calendars/CAL-1/1/exceptions/2026-10-01",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "mode": "total-work-hours", "total_work_hours": "6",
            "intervals": [], "expected_revision": 2,
        }).encode(),
    )
    assert status == 200
    revised = json.loads(body)
    assert revised["record_revision"] == 3
    assert api.calls[-1][0] == "revise_exception"
    assert api.calls[-1][4] == date(2026, 10, 1)
    assert api.calls[-1][5] == "total-work-hours"
    assert api.calls[-1][6] == "6"
    assert api.calls[-1][8] == 2

    status, _, body = r.handle(
        "PUT", "/api/projects/p1/p6/calendars/CAL-1/1/exceptions/2026-10-01",
        cookies={"cp_session": "s1"},
        body=json.dumps({"mode": "nonwork", "intervals": []}).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_CALENDAR_REQUEST_INVALID"


class WorkspaceReadAPI:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def read_workspace_control_room(self, *, tenant_id, project_id, revision, auth_context):
        self.calls.append((tenant_id, project_id, revision, auth_context))
        return self.result


def workspace_read_routes(result):
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
    backend_api = WorkspaceReadAPI(result)
    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        backend_p0_api=backend_api,
    )
    return routes, backend_api


def workspace_snapshot(revision=2):
    return {
        "contract_version": "workspace-control-room-read.v1",
        "context": {"tenant_id": "t1", "project_id": "p1", "revision": revision},
        "workspace": {
            "contract_version": "workspace-control-room.v1",
            "context": {"tenant_id": "t1", "project_id": "p1", "revision": revision},
            "columns": [],
            "activities": [],
        },
        "field_daily_logs": [],
        "field_issues": [],
        "field_timecards": [],
        "equipment_status_reports": [],
        "inspections": [],
        "quality_records": [],
        "safety_observations": [],
        "punch_items": [],
    }


def test_workspace_control_room_read_http_route_uses_authenticated_project_context():
    r, backend = workspace_read_routes(workspace_snapshot())
    status, _, body = r.handle(
        "GET", "/api/v1/workspace/control-room/read",
        cookies={"cp_session": "s1"},
        headers={
            "X-Tenant-Id": "t1",
            "X-Project-Id": "p1",
            "X-Project-Revision": "2",
        },
    )
    assert status == 200
    assert json.loads(body)["contract_version"] == "workspace-control-room-read.v1"
    tenant_id, project_id, revision, auth_context = backend.calls[0]
    assert (tenant_id, project_id, revision) == ("t1", "p1", 2)
    assert auth_context.tenant_id == "t1"
    assert auth_context.project_id == "p1"


def test_workspace_control_room_read_http_route_rejects_missing_or_cross_scope_headers():
    r, backend = workspace_read_routes(workspace_snapshot())
    status, _, body = r.handle(
        "GET", "/api/v1/workspace/control-room/read",
        cookies={"cp_session": "s1"},
        headers={"X-Project-Id": "p1", "X-Project-Revision": "2"},
    )
    assert status == 400
    assert json.loads(body)["code"] == "WORKSPACE_READ_REQUEST_INVALID"
    assert backend.calls == []

    status, _, body = r.handle(
        "GET", "/api/v1/workspace/control-room/read",
        cookies={"cp_session": "s1"},
        headers={
            "X-Tenant-Id": "t1",
            "X-Project-Id": "p2",
            "X-Project-Revision": "2",
        },
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
    assert backend.calls == []


def test_workspace_control_room_read_http_route_preserves_stale_revision_error():
    r, _ = workspace_read_routes({
        "error": {
            "category": "conflict",
            "code": "STALE_WORKSPACE_READ_SCOPE",
            "message": "Workspace snapshot revision does not match the requested scope",
            "retryable": True,
        }
    })
    status, _, body = r.handle(
        "GET", "/api/v1/workspace/control-room/read",
        cookies={"cp_session": "s1"},
        headers={
            "X-Tenant-Id": "t1",
            "X-Project-Id": "p1",
            "X-Project-Revision": "1",
        },
    )
    assert status == 409
    payload = json.loads(body)
    assert payload["error"]["code"] == "STALE_WORKSPACE_READ_SCOPE"
    assert payload["error"]["retryable"] is True


def test_workspace_control_room_read_http_route_rejects_malformed_backend_response():
    r, _ = workspace_read_routes(["not-an-object"])
    status, _, body = r.handle(
        "GET", "/api/v1/workspace/control-room/read",
        cookies={"cp_session": "s1"},
        headers={
            "X-Tenant-Id": "t1",
            "X-Project-Id": "p1",
            "X-Project-Revision": "2",
        },
    )
    assert status == 502
    assert json.loads(body)["code"] == "INVALID_WORKSPACE_READ_RESPONSE"


class ScheduleQueryAPIStub:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, request, *, auth_context):
        self.calls.append((request, auth_context))
        return self.result


def schedule_query_routes(result):
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
    schedule_api = ScheduleQueryAPIStub(result)
    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        schedule_query_api=schedule_api,
    )
    return routes, schedule_api


def schedule_query_payload(*, project_id="p1", tenant_id="t1", revision=2, requested_by="u1"):
    return {
        "contract_version": "schedule-query.v1",
        "query_id": "Q-1",
        "scope": {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "project_revision": revision,
        },
        "requested_by": requested_by,
        "query_text": "show schedule",
        "kind": "fact",
        "language": "en",
        "constraints": {},
    }


def test_schedule_query_http_route_preserves_versioned_result_and_authenticated_scope():
    result = {
        "contract_version": "schedule-query-result.v1",
        "query_id": "Q-1",
        "scope": {"tenant_id": "t1", "project_id": "p1", "project_revision": 2},
        "answer_key": "schedule.query.result",
        "data": {"count": 2},
        "source_refs": [{"source_id": "S-1", "source_type": "schedule", "locator": "/schedule/A-1", "revision": 2}],
        "proposed_actions": [],
    }
    r, api = schedule_query_routes(result)
    status, _, raw = r.handle(
        "POST", "/api/v1/schedule/query",
        cookies={"cp_session": "s1"},
        body=json.dumps(schedule_query_payload()).encode(),
    )
    assert status == 200
    payload = json.loads(raw)
    assert payload["contract_version"] == "schedule-query-result.v1"
    request, auth_context = api.calls[0]
    assert request.scope.tenant_id == "t1"
    assert request.scope.project_id == "p1"
    assert request.scope.project_revision == 2
    assert request.requested_by == "u1"
    assert auth_context.project_id == "p1"


def test_schedule_query_http_route_rejects_cross_scope_and_requested_by_spoofing():
    r, api = schedule_query_routes({})
    status, _, raw = r.handle(
        "POST", "/api/v1/schedule/query",
        cookies={"cp_session": "s1"},
        body=json.dumps(schedule_query_payload(project_id="p2")).encode(),
    )
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
    assert api.calls == []

    status, _, raw = r.handle(
        "POST", "/api/v1/schedule/query",
        cookies={"cp_session": "s1"},
        body=json.dumps(schedule_query_payload(requested_by="other-user")).encode(),
    )
    assert status == 403
    assert json.loads(raw)["code"] == "REQUESTED_BY_MISMATCH"
    assert api.calls == []


def test_schedule_query_http_route_rejects_invalid_request_and_provider_errors():
    r, api = schedule_query_routes({})
    status, _, raw = r.handle(
        "POST", "/api/v1/schedule/query",
        cookies={"cp_session": "s1"},
        body=b"{not-json",
    )
    assert status == 400
    assert json.loads(raw)["code"] == "SCHEDULE_QUERY_REQUEST_INVALID"
    assert api.calls == []

    r, api = schedule_query_routes({
        "error": {
            "category": "conflict",
            "code": "SCHEDULE_QUERY_RESULT_SCOPE_MISMATCH",
            "message": "Schedule query result scope does not match the request",
            "retryable": False,
        }
    })
    status, _, raw = r.handle(
        "POST", "/api/v1/schedule/query",
        cookies={"cp_session": "s1"},
        body=json.dumps(schedule_query_payload()).encode(),
    )
    assert status == 409
    assert json.loads(raw)["error"]["code"] == "SCHEDULE_QUERY_RESULT_SCOPE_MISMATCH"
    assert len(api.calls) == 1


def test_schedule_query_http_route_rejects_invalid_result_contract():
    r, _ = schedule_query_routes({"contract_version": "schedule-query-result.v99"})
    status, _, raw = r.handle(
        "POST", "/api/v1/schedule/query",
        cookies={"cp_session": "s1"},
        body=json.dumps(schedule_query_payload()).encode(),
    )
    assert status == 502
    assert json.loads(raw)["code"] == "INVALID_SCHEDULE_QUERY_RESPONSE"


class SyncHandler:
    def __init__(self):
        self.calls = []
        self.endpoint_factory_calls = 0

    def handle(self, mutation):
        self.calls.append(mutation)


def sync_routes(*, roles=frozenset({"project_admin"})):
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", roles, now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    handler = SyncHandler()
    endpoint = VersionedSyncEndpoint(ApplicationSyncGateway("t1", "p1", handler))
    def endpoint_factory(_tenant, _project):
        handler.endpoint_factory_calls += 1
        return endpoint

    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        sync_endpoint_factory=endpoint_factory,
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
    assert handler.endpoint_factory_calls == 1


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

def relationship_routes():
    import sqlite3
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    relationship_api = P6RelationshipAPI(SQLiteRelationshipMasterRepository(sqlite3.connect(":memory:")), default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_relationship_api=relationship_api,
    )


def test_authenticated_relationship_http_boundary_supports_create_read_list_and_update():
    r = relationship_routes()
    payload = {
        "contract_version": P6_RELATIONSHIP_API_VERSION,
        "relationship_id": "rel-1",
        "predecessor_id": "A-1",
        "successor_id": "A-2",
        "relationship_type": "FS",
        "lag_value": "1.25",
        "lag_unit": DurationUnit.WORKING_DAY.value,
    }
    status, _, raw = r.handle("POST", "/api/projects/p1/p6/relationships", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    assert status == 200
    created = json.loads(raw)
    assert created["contract_version"] == P6_RELATIONSHIP_API_VERSION
    assert created["relationship"]["lag_value"] == "1.25"
    assert created["relationship"]["record_revision"] == 1

    status, _, raw = r.handle("GET", "/api/projects/p1/p6/relationships/rel-1", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(raw) == created

    status, _, raw = r.handle("GET", "/api/projects/p1/p6/relationships", cookies={"cp_session": "s1"})
    assert status == 200
    listed = json.loads(raw)
    assert listed["contract_version"] == P6_RELATIONSHIP_API_VERSION
    assert [item["relationship"]["relationship_id"] for item in listed["relationships"]] == ["rel-1"]

    status, _, raw = r.handle(
        "PATCH", "/api/projects/p1/p6/relationships/rel-1", cookies={"cp_session": "s1"},
        body=json.dumps({**payload, "lag_value": "2.5", "expected_revision": 1}).encode(),
    )
    assert status == 200
    updated = json.loads(raw)
    assert updated["relationship"]["lag_value"] == "2.5"
    assert updated["relationship"]["record_revision"] == 2


def test_relationship_http_boundary_rejects_cross_scope_missing_permission_stale_revision_and_invalid_payload():
    r = relationship_routes()
    status, _, raw = r.handle("GET", "/api/projects/p2/p6/relationships", cookies={"cp_session": "s1"})
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    status, _, raw = r.handle(
        "POST", "/api/projects/p1/p6/relationships", cookies={"cp_session": "s1"},
        body=b"{not-json",
    )
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RELATIONSHIP_REQUEST_INVALID"

    status, _, raw = r.handle(
        "GET", "/api/projects/p1/p6/relationships/missing", cookies={"cp_session": "s1"}
    )
    assert status == 404
    assert json.loads(raw)["code"] == "P6_RELATIONSHIP_NOT_FOUND"

    status, _, raw = r.handle(
        "PATCH", "/api/projects/p1/p6/relationships/missing", cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 1, "predecessor_id": "A", "successor_id": "B", "relationship_type": "FS", "lag_value": "0", "lag_unit": DurationUnit.WORKING_DAY.value}).encode(),
    )
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RELATIONSHIP_REQUEST_INVALID"

    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"viewer"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    import sqlite3
    viewer_api = P6RelationshipAPI(SQLiteRelationshipMasterRepository(sqlite3.connect(":memory:")), default_project_policy())
    viewer_routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_relationship_api=viewer_api,
    )
    status, _, raw = viewer_routes.handle(
        "POST", "/api/projects/p1/p6/relationships", cookies={"cp_session": "s1"},
        body=json.dumps({
            "relationship_id": "rel-v", "predecessor_id": "A", "successor_id": "B",
            "relationship_type": "FS", "lag_value": "0", "lag_unit": DurationUnit.WORKING_DAY.value,
        }).encode(),
    )
    assert status == 403
    assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(raw)["code"]


def resource_assignment_routes():
    import sqlite3
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    connection = sqlite3.connect(":memory:")
    transaction_manager = SQLiteTransactionManager(connection)
    assignment_service = P6ResourceAssignmentApplicationService(SQLiteP6ResourceAssignmentRepository(connection), transaction_manager)
    period_service = P6ResourceAssignmentPeriodApplicationService(SQLiteP6ResourceAssignmentPeriodRepository(connection), transaction_manager)
    assignment_service.save(P6ResourceAssignment(BackendScope("t1", "p1", 2), "A-R-1", "ACT-1", "RES-1", role_id="ROLE-1", units=Decimal("8"), planned_cost=Decimal("100")))
    spread_service = P6ResourceSpreadApplicationService(SQLiteP6ResourceSpreadRepository(connection), transaction_manager)
    read_api = P6ResourceReadAPI(assignment_service, period_service, spread_service, default_project_policy())
    write_api = P6ResourceWriteAPI(
        period_service, default_project_policy(), assignment_service=assignment_service
    )
    return ProjectLifecycleHttpRoutes(ProjectLifecycleAPI(service), clock=type("Clock", (), {"now": lambda self: now})(), p6_resource_read_api=read_api, p6_resource_write_api=write_api)


def test_authenticated_resource_assignment_http_boundary_reads_assignment_and_period():
    r = resource_assignment_routes()
    status, _, raw = r.handle("GET", "/api/projects/p1/p6/resource-assignments/A-R-1", cookies={"cp_session": "s1"})
    assert status == 200
    assignment = json.loads(raw)
    assert assignment["contract_version"] == P6_RESOURCE_READ_API_VERSION
    assert assignment["assignment"]["assignment_id"] == "A-R-1"
    status, _, raw = r.handle("POST", "/api/projects/p1/p6/resource-assignment-periods", cookies={"cp_session": "s1"}, body=json.dumps({"assignment_id":"A-R-1","activity_id":"ACT-1","resource_id":"RES-1","period_start":"2026-10-01","units":"4","cost":"50"}).encode())
    assert status == 200
    period = json.loads(raw)
    assert period["contract_version"] == P6_RESOURCE_WRITE_API_VERSION
    status, _, raw = r.handle("GET", "/api/projects/p1/p6/resource-assignment-periods/A-R-1/2026-10-01", cookies={"cp_session": "s1"})
    assert status == 200
    fetched = json.loads(raw)
    assert fetched["kind"] == period["kind"]
    assert fetched["scope"] == period["scope"]
    assert fetched["period"] == period["period"]



def test_authenticated_resource_assignment_write_persists_driving_and_rate_fields():
    r = resource_assignment_routes()
    payload = {
        "contract_version": P6_RESOURCE_WRITE_API_VERSION,
        "assignment_id": "A-R-DRIVING",
        "activity_id": "ACT-1",
        "resource_id": "RES-1",
        "units": "16",
        "remaining_units": "12",
        "unit": "labor-unit",
        "calendar_id": "RES-CAL-1",
        "calendar_version": "v2",
        "is_driving": True,
        "units_per_time": "4",
        "units_per_time_period": "day",
        "hours_per_units_time_period": "8",
    }
    status, _, raw = r.handle(
        "POST", "/api/projects/p1/p6/resource-assignments",
        cookies={"cp_session": "s1"}, body=json.dumps(payload).encode(),
    )

    assert status == 200
    saved = json.loads(raw)
    assert saved["contract_version"] == P6_RESOURCE_WRITE_API_VERSION
    assert saved["kind"] == "resource_assignment"
    assert saved["assignment"]["is_driving"] is True
    assert saved["assignment"]["units_per_time"] == "4"
    assert saved["assignment"]["units_per_time_period"] == "day"
    assert saved["assignment"]["hours_per_units_time_period"] == "8"

    status, _, raw = r.handle(
        "GET", "/api/projects/p1/p6/resource-assignments/A-R-DRIVING",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    reread = json.loads(raw)
    assert reread["assignment"]["is_driving"] is True
    assert reread["assignment"]["units_per_time"] == "4"
    assert reread["assignment"]["hours_per_units_time_period"] == "8"


def test_resource_assignment_write_rejects_ambiguous_driving_flag_and_missing_contract():
    r = resource_assignment_routes()
    payload = {
        "contract_version": P6_RESOURCE_WRITE_API_VERSION,
        "assignment_id": "A-R-INVALID",
        "activity_id": "ACT-1",
        "resource_id": "RES-1",
        "calendar_id": "RES-CAL-1",
        "calendar_version": "v2",
        "is_driving": "true",
    }
    status, _, raw = r.handle(
        "POST", "/api/projects/p1/p6/resource-assignments",
        cookies={"cp_session": "s1"}, body=json.dumps(payload).encode(),
    )
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID"

    payload.pop("contract_version")
    payload["is_driving"] = True
    status, _, raw = r.handle(
        "POST", "/api/projects/p1/p6/resource-assignments",
        cookies={"cp_session": "s1"}, body=json.dumps(payload).encode(),
    )
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID"

def test_resource_assignment_http_boundary_enforces_scope_and_payload():
    r = resource_assignment_routes()
    status, _, raw = r.handle("GET", "/api/projects/p2/p6/resource-assignments", cookies={"cp_session": "s1"})
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
    status, _, raw = r.handle("POST", "/api/projects/p1/p6/resource-assignment-periods", cookies={"cp_session": "s1"}, body=b"{not-json")
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RESOURCE_REQUEST_INVALID"

def resource_spread_routes():
    import sqlite3
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    connection = sqlite3.connect(":memory:")
    spread_service = P6ResourceSpreadApplicationService(
        SQLiteP6ResourceSpreadRepository(connection),
        SQLiteTransactionManager(connection),
    )
    spread_api = P6ResourceSpreadAPI(spread_service, default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_resource_spread_api=spread_api,
    )


def test_authenticated_resource_spread_http_boundary_round_trips_typed_bucket():
    r = resource_spread_routes()
    body = {
        "spread_id": "spread-1", "resource_id": "R-1", "period_id": "2026-10",
        "period_start": "2026-10-01", "period_end": "2026-10-31",
        "spread_type": "FORECAST", "metric": "COST", "value": "1234.5678",
        "currency": "USD",
    }
    status, _, raw = r.handle(
        "POST", "/api/projects/p1/p6/resource-spreads",
        cookies={"cp_session": "s1"}, body=json.dumps(body).encode(),
    )
    assert status == 200
    created = json.loads(raw)
    assert created["contract_version"] == P6_RESOURCE_SPREAD_API_VERSION
    assert created["spread"]["value"] == "1234.5678"
    assert created["spread"]["currency"] == "USD"

    status, _, raw = r.handle(
        "GET", "/api/projects/p1/p6/resource-spreads/spread-1/2026-10",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(raw) == created

    status, _, raw = r.handle(
        "GET", "/api/projects/p1/p6/resource-spreads", cookies={"cp_session": "s1"}
    )
    assert status == 200
    listed = json.loads(raw)
    assert listed["contract_version"] == P6_RESOURCE_SPREAD_API_VERSION
    assert listed["buckets"] == [created]


def test_resource_spread_http_boundary_enforces_project_scope_and_payload_contract():
    r = resource_spread_routes()
    status, _, raw = r.handle(
        "GET", "/api/projects/p2/p6/resource-spreads", cookies={"cp_session": "s1"}
    )
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    status, _, raw = r.handle(
        "POST", "/api/projects/p1/p6/resource-spreads",
        cookies={"cp_session": "s1"}, body=b"{not-json",
    )
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RESOURCE_SPREAD_REQUEST_INVALID"

    invalid = {
        "spread_id": "spread-1", "resource_id": "R-1", "period_id": "2026-10",
        "period_start": "2026-10-01", "period_end": "2026-10-31",
        "spread_type": "FORECAST", "metric": "UNITS", "value": "10",
        "currency": "USD",
    }
    status, _, raw = r.handle(
        "POST", "/api/projects/p1/p6/resource-spreads",
        cookies={"cp_session": "s1"}, body=json.dumps(invalid).encode(),
    )
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RESOURCE_SPREAD_REQUEST_INVALID"

def p6_code_routes(roles=frozenset({"project_admin"})):
    import sqlite3
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", roles, now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    connection = sqlite3.connect(":memory:")
    transaction_manager = SQLiteTransactionManager(connection)
    code_api = P6CodeAPI(
        P6CodeApplicationService(SQLiteP6CodeRepository(connection), transaction_manager),
        default_project_policy(),
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_code_api=code_api,
    )


def test_authenticated_p6_code_http_boundary_round_trips_typed_definition():
    r = p6_code_routes()
    payload = {
        "code_id": "ACT-PHASE", "name": "Activity Phase", "subject_area": "Activity",
        "scope_kind": "PROJECT", "scope_key": "p1",
        "values": [{"value_id": "DES", "value": "Design", "description": "Design phase"}],
    }
    status, _, raw = r.handle("POST", "/api/projects/p1/p6/codes", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    assert status == 200
    created = json.loads(raw)
    assert created["contract_version"] == P6_CODE_API_VERSION
    assert created["code"]["code_id"] == "ACT-PHASE"
    assert created["code"]["values"][0]["value"] == "Design"
    status, _, raw = r.handle("GET", "/api/projects/p1/p6/codes/ACT-PHASE", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(raw) == created
    status, _, raw = r.handle("GET", "/api/projects/p1/p6/codes", cookies={"cp_session": "s1"})
    assert status == 200
    listed = json.loads(raw)
    assert listed["contract_version"] == P6_CODE_API_VERSION
    assert [item["code"]["code_id"] for item in listed["codes"]] == ["ACT-PHASE"]


def test_p6_code_http_boundary_enforces_scope_permission_and_payload_contract():
    r = p6_code_routes()
    status, _, raw = r.handle("GET", "/api/projects/p2/p6/codes", cookies={"cp_session": "s1"})
    assert status == 403
    assert json.loads(raw)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"
    r = p6_code_routes(roles=frozenset())
    status, _, raw = r.handle("GET", "/api/projects/p1/p6/codes", cookies={"cp_session": "s1"})
    assert status == 403
    assert "authorization" in json.loads(raw)["code"].lower()
    r = p6_code_routes()
    status, _, raw = r.handle("POST", "/api/projects/p1/p6/codes", cookies={"cp_session": "s1"}, body=b"{not-json")
    assert status == 400
    assert json.loads(raw)["code"] == "P6_CODE_REQUEST_INVALID"
    status, _, raw = r.handle("GET", "/api/projects/p1/p6/codes/missing", cookies={"cp_session": "s1"})
    assert status == 404
    assert json.loads(raw)["code"] == "P6_CODE_NOT_FOUND"

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


def test_session_response_never_reflects_the_session_credential():
    r = routes()
    status, _, body = r.handle("GET", "/api/session", cookies={"cp_session": "s1"})
    assert status == 200
    payload = json.loads(body)
    assert "session_id" not in payload
    assert "s1" not in body.decode("utf-8")
    assert payload["user_id"] == "u1"
    assert payload["tenant_id"] == "t1"


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
    formula_column_service = P6FormulaColumnService(
        P6FieldRegistryApplicationService(
            SQLiteP6FieldRegistryRepository(connection), transaction_manager
        ),
        P6FormulaDefinitionApplicationService(
            SQLiteP6FormulaDefinitionRepository(connection), transaction_manager
        ),
    )
    field_api = P6FieldRegistryAPI(
        formula_column_service.field_service,
        P6UserDefinedFieldApplicationService(SQLiteP6UserDefinedFieldRepository(connection), transaction_manager),
        default_project_policy(),
        formula_column_service,
    )
    udf_repository = SQLiteP6UserDefinedFieldRepository(connection)
    udf_value_api = P6UserDefinedFieldValueAPI(
        P6UserDefinedFieldValueApplicationService(
            SQLiteP6UserDefinedFieldValueRepository(connection),
            udf_repository,
            transaction_manager,
        ),
        default_project_policy(),
    )
    layout_api = P6LayoutDefinitionAPI(SQLiteP6LayoutRepository(connection), default_project_policy())
    formula_api = P6FormulaAuthorityAPI(
        formula_column_service.field_service,
        default_project_policy(),
        formula_column_service,
    )
    formula_column_api = P6FormulaColumnAPI(formula_column_service, default_project_policy())
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
        p6_udf_value_api=udf_value_api,
        p6_layout_definition_api=layout_api,
        p6_formula_authority_api=formula_api,
        p6_formula_column_api=formula_column_api,
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


def test_p6_formula_route_returns_structured_unsupported_field_result():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.percent_complete"), auth_context=auth)
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.planned_duration"), auth_context=auth)
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formulas/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expression": "[activity.planned_duration] * 2"}).encode("utf-8"),
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == P6_FORMULA_AUTHORITY_API_VERSION
    assert payload["validation"]["valid"] is False
    assert (
        payload["validation"]["error_code"]
        == "UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration"
    )
    assert payload["dependencies"]["field_ids"] == []
    assert payload["result_type"]["data_type"] is None


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


def test_p6_formula_column_route_creates_lists_and_projects_into_registry():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    field_api.save_field(scope, "p6-field-registry.v1", get_field("activity.percent_complete"), auth_context=auth)

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/formula-columns",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(body)["formula_columns"] == []

    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formula-columns",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "formula_id": "formula.double_progress",
            "title": "Double Progress",
            "expression": "[activity.percent_complete] * 2",
        }).encode("utf-8"),
    )
    assert status == 200
    created = json.loads(body)
    assert created["contract_version"] == "p6-formula-column-api.v1"
    assert created["kind"] == "formula_column"
    assert created["formula"]["formula_id"] == "formula.double_progress"
    assert created["formula"]["data_type"] == "double"

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/formula-columns",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    listed = json.loads(body)
    assert listed["kind"] == "formula_column_list"
    assert [item["formula"]["formula_id"] for item in listed["formula_columns"]] == [
        "formula.double_progress"
    ]

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/fields/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    by_id = {item["field_id"]: item for item in json.loads(body)["fields"]}
    assert by_id["formula.double_progress"]["computed"] is True
    assert by_id["formula.double_progress"]["formula"] == "[activity.percent_complete] * 2"


def test_p6_formula_column_route_rejects_invalid_payload_and_cross_project():
    r, _, _ = p6_routes()

    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formula-columns",
        cookies={"cp_session": "s1"},
        body=json.dumps({"formula_id": "formula.x"}).encode("utf-8"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_FORMULA_COLUMN_REQUEST_INVALID"

    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/formula-columns",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "formula_id": "plain_name",
            "title": "Bad",
            "expression": "1",
        }).encode("utf-8"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "INVALID_FORMULA_COLUMN_ID"

    status, _, body = r.handle(
        "GET",
        "/api/projects/p2/p6/formula-columns",
        cookies={"cp_session": "s1"},
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/formula-columns",
    )
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


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


def test_p6_layout_default_route_returns_canonical_columns():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/activity/default",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == "p6-layout-definition-api.v1"
    assert payload["schema_version"] == "p6-layout.v1"
    assert payload["view_id"] == "activity"
    assert payload["revision"] == 0
    assert [column["field_id"] for column in payload["columns"]][:2] == ["activity.id", "activity.name"]
    # The default is a read; it must not have saved a revision.
    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/activity",
        cookies={"cp_session": "s1"},
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_LAYOUT_NOT_FOUND"

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/resource/default",
        cookies={"cp_session": "s1"},
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_LAYOUT_DEFAULT_NOT_DEFINED"


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


def test_p6_layout_write_route_retry_is_idempotent():
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
    for _ in range(2):
        status, _, body = r.handle(
            "POST",
            "/api/projects/p1/p6/layouts/project/activity",
            cookies={"cp_session": "s1"},
            body=json.dumps(payload).encode("utf-8"),
        )
        assert status == 200
        assert json.loads(body)["revision"] == 1

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/activity/revisions",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    revisions = json.loads(body)["revisions"]
    assert [item["revision"] for item in revisions] == [1]
    assert revisions[0]["columns"][0]["width"] == 120.0


def test_p6_layout_write_route_reports_stale_and_immutable_writes_as_409():
    r, _, _ = p6_routes()

    def write(revision: int, width: float):
        column = {
            "field_id": "activity_id",
            "visible": True,
            "order": 0,
            "label": None,
            "width": width,
            "alignment": "start",
            "pinned": False,
            "frozen": False,
        }
        return r.handle(
            "POST",
            "/api/projects/p1/p6/layouts/project/activity",
            cookies={"cp_session": "s1"},
            body=json.dumps({
                "revision": revision,
                "columns": [column],
                "metadata": {},
            }).encode("utf-8"),
        )

    assert write(2, 120.0)[0] == 200
    assert write(3, 180.0)[0] == 200

    # A client behind the head must reload instead of rewriting history.
    status, _, body = write(2, 300.0)
    assert status == 409
    assert json.loads(body)["code"] == "REVISION_CONFLICT"
    assert json.loads(body)["message_key"] == "error.p6.layout.conflict"

    # Publishing different content under an existing revision is immutable.
    status, _, body = write(3, 300.0)
    assert status == 409
    assert json.loads(body)["code"] == "IMMUTABLE_LAYOUT_REVISION"

    # Rejected writes leave the published head untouched.
    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/activity",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    head = json.loads(body)
    assert head["revision"] == 3
    assert head["columns"][0]["width"] == 180.0


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


def test_p6_layout_history_route_returns_append_only_revisions():
    r, _, layout_api = p6_routes()
    layout_api.repository.upsert(PersistedP6Layout(
        BackendScope("t1", "p1", 2), "project", "activity", 1,
        (LayoutColumn("activity_id", True, 0, None, 120, "start", False, False),),
        {"density": "compact"},
    ))
    layout_api.repository.upsert(PersistedP6Layout(
        BackendScope("t1", "p1", 2), "project", "activity", 2,
        (LayoutColumn("activity_id", True, 0, None, 180, "start", False, False),),
        {"density": "compact"},
    ))
    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/layouts/project/activity/revisions",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["contract_version"] == "p6-layout-definition-api.v1"
    assert payload["kind"] == "layout_definition_history"
    assert [item["revision"] for item in payload["revisions"]] == [2, 1]
    assert payload["revisions"][0]["columns"][0]["width"] == 180
    assert payload["revisions"][1]["columns"][0]["width"] == 120

    # Reading history must not append or renumber a revision.
    status, _, current = r.handle(
        "GET", "/api/projects/p1/p6/layouts/project/activity", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(current)["revision"] == 2

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


def test_p6_udf_route_lists_seeded_lowercase_activity_definitions():
    r, field_api, _ = p6_routes()
    scope = BackendScope("t1", "p1", 2)
    auth = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    field_api.save_udf(
        P6UserDefinedFieldDefinition(
            scope=scope,
            registry_version="p6-field-registry.v1",
            udf_id="activity.seeded_status",
            subject_area="activity",
            display_name="Seeded Status",
            data_type=P6FieldType.STRING,
            writable=True,
            nullable=True,
            unit=None,
            allowed_values=(),
        ),
        auth_context=auth,
    )

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )

    assert status == 200
    assert [item["udf_id"] for item in json.loads(body)["udfs"]] == [
        "activity.seeded_status"
    ]


def test_p6_udf_route_rejects_cross_scope_project_context():
    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "GET",
        "/api/projects/p2/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_p6_udf_value_http_routes_round_trip_typed_values():
    r, _, _ = p6_routes()
    definition = {
        "udf_id": "activity.contract_status",
        "subject_area": "Activity",
        "display_name": "Contract Status",
        "data_type": "enum",
        "writable": True,
        "nullable": True,
        "unit": None,
        "allowed_values": ["draft", "signed", "closed"],
    }
    status, _, _ = r.handle(
        "POST",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps(definition).encode("utf-8"),
    )
    assert status == 200

    base = "/api/projects/p1/p6/udf-values/p6-field-registry.v1/activity/A-100"
    status, _, body = r.handle(
        "PUT",
        f"{base}/activity.contract_status",
        cookies={"cp_session": "s1"},
        body=json.dumps({"value": "signed"}).encode("utf-8"),
    )
    assert status == 200
    saved = json.loads(body)
    assert saved["contract_version"] == "p6-udf-value-api.v1"
    assert saved["kind"] == "user_defined_field_value"
    assert saved["object_type"] == "activity"
    assert saved["object_id"] == "A-100"
    assert saved["udf_id"] == "activity.contract_status"
    assert saved["value"] == "signed"

    status, _, body = r.handle(
        "GET", base, cookies={"cp_session": "s1"}
    )
    assert status == 200
    payload = json.loads(body)
    assert payload["kind"] == "user_defined_field_value_list"
    assert payload["object_type"] == "activity"
    assert payload["object_id"] == "A-100"
    assert [item["udf_id"] for item in payload["values"]] == ["activity.contract_status"]
    assert payload["values"][0]["value"] == "signed"

    status, _, body = r.handle(
        "PUT",
        f"{base}/activity.contract_status",
        cookies={"cp_session": "s1"},
        body=json.dumps({"value": None}).encode("utf-8"),
    )
    assert status == 200
    assert json.loads(body)["value"] is None


def test_p6_udf_value_http_routes_reject_invalid_and_unknown_writes():
    r, _, _ = p6_routes()
    status, _, _ = r.handle(
        "POST",
        "/api/projects/p1/p6/udfs/p6-field-registry.v1",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "udf_id": "activity.stage",
            "subject_area": "Activity",
            "display_name": "Stage",
            "data_type": "enum",
            "writable": True,
            "nullable": False,
            "allowed_values": ["draft", "active"],
        }).encode("utf-8"),
    )
    assert status == 200
    base = "/api/projects/p1/p6/udf-values/p6-field-registry.v1/activity/A-100"

    status, _, body = r.handle(
        "PUT", f"{base}/activity.stage", cookies={"cp_session": "s1"},
        body=json.dumps({"value": "unknown"}).encode("utf-8"),
    )
    assert status == 400
    assert json.loads(body)["code"] == "INVALID_ENUM_VALUE"

    status, _, body = r.handle(
        "PUT", f"{base}/activity.missing", cookies={"cp_session": "s1"},
        body=json.dumps({"value": "draft"}).encode("utf-8"),
    )
    assert status == 404
    assert json.loads(body)["code"] == "UDF_NOT_FOUND"

    status, _, body = r.handle(
        "PUT", f"{base}/activity.stage", cookies={"cp_session": "s1"},
        body=b"not-json",
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_UDF_VALUE_REQUEST_INVALID"

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/udf-values/p6-field-registry.v1/wbs/W-1",
        cookies={"cp_session": "s1"},
    )
    assert status == 400
    assert json.loads(body)["code"] == "UNSUPPORTED_UDF_OBJECT_TYPE"

    status, _, body = r.handle(
        "GET",
        "/api/projects/p1/p6/udf-values/p6-field-registry.v1/activity",
        cookies={"cp_session": "s1"},
    )
    assert status == 400
    assert json.loads(body)["code"] == "P6_UDF_VALUE_REQUEST_INVALID"


def test_p6_udf_value_http_routes_gate_writes_by_role_and_session():
    r, _, _ = p6_routes(frozenset({"viewer"}))
    base = "/api/projects/p1/p6/udf-values/p6-field-registry.v1/activity/A-100"
    status, _, body = r.handle("GET", base, cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["values"] == []

    status, _, body = r.handle(
        "PUT",
        f"{base}/activity.stage",
        cookies={"cp_session": "s1"},
        body=json.dumps({"value": "draft"}).encode("utf-8"),
    )
    assert status == 403
    assert json.loads(body)["code"] == "P6_UDF_VALUE_PERMISSION_DENIED"

    status, _, body = r.handle("GET", base)
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


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
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"

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
    assert "%R\tA-100" in exported["document"]["data"]


def test_p6_interchange_http_requires_scope_and_permission():
    r, _, _ = p6_routes(roles=frozenset({"viewer"}))
    status, _, body = r.handle(
        "POST", "/api/projects/p1/p6/interchange/XER_PROJECT/import",
        cookies={"cp_session": "s1"}, body=b"%T\tTASK\n%F\ttask_code\n%R\tA-100\n%E\n",
    )
    assert status == 403
    assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(body)["code"]

    r, _, _ = p6_routes()
    status, _, body = r.handle(
        "POST", "/api/projects/p2/p6/interchange/XER_PROJECT/import",
        cookies={"cp_session": "s1"}, body=b"%T\tTASK\n%F\ttask_code\n%R\tA-100\n%E\n",
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


class _WsgiRoutesStub:
    def __init__(self):
        self.calls = []

    def handle(self, method, path, *, cookies=None, body=b"", headers=None):
        self.calls.append((method, path, body))
        return 200, {"Content-Type": "application/json; charset=utf-8"}, b"{}"


def _wsgi_environ(path, body):
    return {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }


def test_wsgi_allows_configured_p6_import_payload_above_default_limit():
    routes = _WsgiRoutesStub()
    app = ProjectLifecycleWsgiApp(routes, default_body_limit=10, p6_import_body_limit=20)
    body = b"x" * 15
    statuses = []
    app(_wsgi_environ("/api/projects/p1/p6/interchange/XER_PROJECT/import", body), lambda status, headers: statuses.append(status))
    assert statuses == ["200 OK"]
    assert routes.calls[0][2] == body


def test_wsgi_rejects_oversized_p6_import_before_route_layer():
    routes = _WsgiRoutesStub()
    app = ProjectLifecycleWsgiApp(routes, default_body_limit=10, p6_import_body_limit=20)
    body = b"x" * 21
    statuses = []
    captured = []
    result = app(_wsgi_environ("/api/projects/p1/p6/interchange/XER_PROJECT/import", body), lambda status, headers: (statuses.append(status), captured.extend(headers)))
    assert statuses == ["413 Payload Too Large"]
    assert routes.calls == []
    assert b"REQUEST_BODY_TOO_LARGE" in result[0]


def test_wsgi_rejects_truncated_body_instead_of_dispatching():
    class _ShortStream:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def read(self, size: int = -1) -> bytes:
            if size < 0:
                size = len(self.data)
            chunk, self.data = self.data[:size], self.data[size:]
            return chunk

    routes = _WsgiRoutesStub()
    app = ProjectLifecycleWsgiApp(routes, default_body_limit=100, p6_import_body_limit=100)
    environ = _wsgi_environ("/api/v1/schedule/query", b"x" * 10)
    environ["wsgi.input"] = _ShortStream(b"x" * 9)
    statuses = []
    result = app(environ, lambda status, headers: statuses.append(status))
    assert statuses == ["400 Bad Request"]
    assert routes.calls == []
    assert b"REQUEST_BODY_INCOMPLETE" in result[0]


def test_wsgi_reads_a_body_delivered_in_several_short_chunks():
    class _ChunkedStream:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def read(self, size: int = -1) -> bytes:
            chunk, self.data = self.data[:2], self.data[2:]
            return chunk

    routes = _WsgiRoutesStub()
    app = ProjectLifecycleWsgiApp(routes, default_body_limit=100, p6_import_body_limit=100)
    body = b"abcdefghij"
    environ = _wsgi_environ("/api/v1/schedule/query", body)
    environ["wsgi.input"] = _ChunkedStream(body)
    statuses = []
    app(environ, lambda status, headers: statuses.append(status))
    assert statuses == ["200 OK"]
    assert routes.calls[0][2] == body


def test_wsgi_keeps_default_limit_for_non_import_endpoints():
    routes = _WsgiRoutesStub()
    app = ProjectLifecycleWsgiApp(routes, default_body_limit=10, p6_import_body_limit=20)
    body = b"x" * 11
    statuses = []
    result = app(_wsgi_environ("/api/v1/schedule/query", body), lambda status, headers: statuses.append(status))
    assert statuses == ["413 Payload Too Large"]
    assert routes.calls == []
    assert b"REQUEST_BODY_TOO_LARGE" in result[0]


def change_claim_routes():
    now = datetime(2026, 10, 9, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    repository = InMemoryChangeClaimRepository()
    change_claim_api = ChangeClaimAPI(
        ChangeClaimService(repository), repository, default_project_policy()
    )
    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        change_claim_api=change_claim_api,
    )
    return routes, repository


def test_change_claim_http_create_and_get_use_authenticated_scope_and_actor():
    r, repository = change_claim_routes()
    payload = {
        "contract_version": P0_CHANGE_CLAIM_API_VERSION,
        "resource_id": "CC-1",
        "revision": 0,
        "resource_type": "change",
        "status": "draft",
        "occurred_at": "2026-10-09T10:00:00Z",
        "payload": {"title": "Site instruction"},
        "evidence_refs": ["doc-1"],
        "expected_revision": 0,
        "idempotency_key": "create-cc-1",
        # Deliberately malicious: actor identity must come from the session.
        "actor_id": "another-user",
        "tenant_id": "another-tenant",
        "project_id": "another-project",
    }
    status, _, body = r.handle(
        "POST", "/api/projects/p1/change-claims",
        cookies={"cp_session": "s1"}, body=json.dumps(payload).encode(),
    )
    assert status == 201
    created = json.loads(body)
    assert created["contract_version"] == P0_CHANGE_CLAIM_API_VERSION
    assert created["tenant_id"] == "t1"
    assert created["project_id"] == "p1"
    assert created["actor_id"] == "u1"
    assert created["evidence_refs"] == ["doc-1"]
    assert repository.get("t1", "p1", "CC-1") is not None
    assert repository.get("another-tenant", "another-project", "CC-1") is None

    status, _, body = r.handle(
        "GET", "/api/projects/p1/change-claims/CC-1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(body)["resource_id"] == "CC-1"


def test_change_claim_http_rejects_malformed_payload_and_unknown_project():
    r, _ = change_claim_routes()
    status, _, body = r.handle(
        "POST", "/api/projects/p1/change-claims",
        cookies={"cp_session": "s1"}, body=b"{",
    )
    assert status == 400
    assert json.loads(body)["code"] == "CHANGE_CLAIM_REQUEST_INVALID"

    status, _, body = r.handle(
        "GET", "/api/projects/not-a-project/change-claims/CC-1",
        cookies={"cp_session": "s1"},
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"



def test_authenticated_relationship_http_delete_supports_revision_and_not_found():
    r = relationship_routes()
    payload = {
        "relationship_id": "rel-delete", "predecessor_id": "A-1", "successor_id": "A-2",
        "relationship_type": "SF", "lag_value": "-1.25",
        "lag_unit": DurationUnit.WORKING_HOUR.value,
    }
    status, _, raw = r.handle("POST", "/api/projects/p1/p6/relationships", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    assert status == 200
    assert json.loads(raw)["relationship"]["record_revision"] == 1
    status, _, raw = r.handle(
        "DELETE", "/api/projects/p1/p6/relationships/rel-delete", cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 1, "tenant_id": "attacker", "project_id": "attacker"}).encode(),
    )
    assert status == 200
    deleted = json.loads(raw)
    assert deleted["deleted"] is True
    assert deleted["scope"]["tenant_id"] == "t1"
    assert deleted["scope"]["project_id"] == "p1"
    status, _, raw = r.handle("GET", "/api/projects/p1/p6/relationships/rel-delete", cookies={"cp_session": "s1"})
    assert status == 404
    assert json.loads(raw)["code"] == "P6_RELATIONSHIP_NOT_FOUND"


def test_authenticated_relationship_http_delete_rejects_stale_and_missing_revision():
    r = relationship_routes()
    payload = {
        "relationship_id": "rel-delete", "predecessor_id": "A-1", "successor_id": "A-2",
        "relationship_type": "FS", "lag_value": "0", "lag_unit": DurationUnit.WORKING_DAY.value,
    }
    r.handle("POST", "/api/projects/p1/p6/relationships", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    status, _, raw = r.handle(
        "DELETE", "/api/projects/p1/p6/relationships/rel-delete", cookies={"cp_session": "s1"},
        body=json.dumps({"expected_revision": 9}).encode(),
    )
    assert status == 409
    assert json.loads(raw)["code"] == "REVISION_CONFLICT"
    status, _, raw = r.handle(
        "DELETE", "/api/projects/p1/p6/relationships/rel-delete", cookies={"cp_session": "s1"},
        body=json.dumps({}).encode(),
    )
    assert status == 400
    assert json.loads(raw)["code"] == "P6_RELATIONSHIP_REQUEST_INVALID"


def test_authenticated_sync_mutation_requires_project_write_permission():
    r, handler = sync_routes(roles=frozenset({"viewer"}))
    body = {
        "contract_version": "sync-mutation.v1",
        "mutation_id": "m-viewer",
        "tenant_id": "t1",
        "project_id": "p1",
        "expected_revision": 2,
        "operation": "update_activity",
        "payload": {"activity_id": "A-1"},
        "idempotency_key": "idem-viewer",
    }
    status, _, raw = r.handle(
        "POST", "/api/v1/sync/mutations", cookies={"cp_session": "s1"},
        headers={"Idempotency-Key": "idem-viewer"}, body=json.dumps(body).encode(),
    )

    assert status == 403
    assert json.loads(raw)["code"] == "AUTHORIZATION_PERMISSION_DENIED"
    assert handler.calls == []
    assert handler.endpoint_factory_calls == 0


def test_authenticated_schedule_code_reference_endpoint_returns_safe_catalogue():
    import json

    routes, _, _ = p6_routes()
    status, headers, body = routes.handle(
        "GET", "/api/v1/schedule/code-reference", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    payload = json.loads(body)
    assert payload["contract_version"] == "schedule-code-reference.v1"
    assert payload["requirements"]
    assert payload["formulas"]
    assert payload["summary"]["parity_claimed_complete"] is False
    serialized = body.decode("utf-8").lower()
    assert "oracle" not in serialized
    assert "primavera" not in serialized
    assert "https://" not in serialized

    unauthenticated_status, _, unauthenticated_body = routes.handle(
        "GET", "/api/v1/schedule/code-reference"
    )
    assert unauthenticated_status == 401
    assert json.loads(unauthenticated_body)["code"] == "SESSION_REQUIRED"


def test_project_http_create_persists_metadata_and_reads_it_back():
    r = routes()
    status, _, body = r.handle(
        "POST", "/api/projects",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "project_id": "p7",
            "name": "CUBI Project",
            "description": "Bridge package",
            "start_date": "2026-11-02",
            "date_system": "jalali",
        }).encode(),
    )
    assert status == 201
    assert json.loads(body)["context"]["project_id"] == "p7"

    status, _, body = r.handle(
        "GET", "/api/projects/p7", cookies={"cp_session": "s1"}
    )
    assert status == 200
    project = json.loads(body)["project"]
    assert project["name"] == "CUBI Project"
    assert project["description"] == "Bridge package"
    assert project["start_date"] == "2026-11-02"
    assert project["date_system"] == "jalali"
    assert project["revision"] == 0

    status, _, body = r.handle(
        "GET", "/api/projects", cookies={"cp_session": "s1"}
    )
    listed = {item["project_id"]: item for item in json.loads(body)["projects"]}
    assert listed["p7"]["date_system"] == "jalali"


def test_project_http_business_domain_persists_and_is_preserved_when_omitted():
    r = routes()
    status, _, body = r.handle(
        "POST", "/api/projects",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "project_id": "p8",
            "name": "Domain Project",
            "business_domain": "infrastructure",
        }).encode(),
    )
    assert status == 201

    status, _, body = r.handle("GET", "/api/projects/p8", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["project"]["business_domain"] == "infrastructure"

    status, _, body = r.handle(
        "PATCH", "/api/projects/p8",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Domain Project Renamed", "expected_revision": 0}).encode(),
    )
    assert status == 200, body
    assert json.loads(body)["project"]["business_domain"] == "infrastructure"

    status, _, body = r.handle(
        "PATCH", "/api/projects/p8",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "name": "Domain Project Renamed",
            "business_domain": "energy",
            "expected_revision": 1,
        }).encode(),
    )
    assert status == 200, body
    assert json.loads(body)["project"]["business_domain"] == "energy"

    status, _, body = r.handle(
        "PATCH", "/api/projects/p8",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "name": "Domain Project Renamed",
            "business_domain": "not-a-domain",
            "expected_revision": 2,
        }).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "PROJECT_BUSINESS_DOMAIN_INVALID"


def test_project_http_patch_updates_metadata_under_expected_revision():
    r = routes()
    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "name": "Project One Renamed",
            "description": "Updated",
            "start_date": "2026-12-01",
            "date_system": "gregorian",
            "primary_calendar_id": "CAL-9",
            "expected_revision": 0,
        }).encode(),
    )
    assert status == 200
    project = json.loads(body)["project"]
    assert project["name"] == "Project One Renamed"
    assert project["settings_revision"] == 1
    assert project["revision"] == 2, (
        "editing metadata must not invalidate the workspace data revision"
    )
    assert project["primary_calendar_id"] == "CAL-9"


def test_project_http_patch_rejects_stale_revision_with_409():
    r = routes()
    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Stale", "expected_revision": 1}).encode(),
    )
    assert status == 409
    assert json.loads(body)["code"] == "PROJECT_REVISION_CONFLICT"

    status, _, body = r.handle(
        "GET", "/api/projects/p1", cookies={"cp_session": "s1"}
    )
    assert json.loads(body)["project"]["name"] == "Project One"


def test_project_http_patch_rejects_missing_revision_and_invalid_metadata():
    r = routes()
    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "No Revision"}).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "PROJECT_REVISION_INVALID"

    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Bad Date", "start_date": "2026-13-01", "expected_revision": 2}).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "PROJECT_START_DATE_INVALID"


def test_viewer_cannot_patch_project_metadata():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"viewer"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    r = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
    )
    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Viewer Rename", "expected_revision": 2}).encode(),
    )
    assert status == 403
    assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(body)["code"]


def test_project_http_get_unknown_project_is_forbidden():
    r = routes()
    status, _, body = r.handle(
        "GET", "/api/projects/p-missing", cookies={"cp_session": "s1"}
    )
    assert status == 403
    assert json.loads(body)["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


class _ExplodingActivityAPI:
    """Raise an internal fault the route layer must not reflect."""

    def list(self, _scope, *, auth_context):
        raise KeyError("INTERNAL_SECRET")


def test_stable_error_code_never_returns_internal_detail():
    assert _stable_error_code(KeyError("INTERNAL_SECRET"), "REQUEST_INVALID") == "REQUEST_INVALID"
    assert _stable_error_code(TypeError("unsupported operand"), "REQUEST_INVALID") == "REQUEST_INVALID"
    assert (
        _stable_error_code(
            ValueError("authorization denied for permission=project.write"),
            "AUTHORIZATION_DENIED",
        )
        == "AUTHORIZATION_PERMISSION_DENIED"
    )
    assert (
        _stable_error_code(
            ValueError("INVALID_AUTHORIZATION_USER_ID"), "AUTHORIZATION_DENIED"
        )
        == "INVALID_AUTHORIZATION_CONTEXT"
    )
    assert (
        _stable_error_code(ValueError("REVISION_CONFLICT"), "REQUEST_INVALID")
        == "REVISION_CONFLICT"
    )


def test_unexpected_route_fault_returns_a_fixed_internal_error_code():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_activity_master_api=_ExplodingActivityAPI(),
    )
    status, _, body = routes.handle(
        "GET", "/api/projects/p1/p6/activities", cookies={"cp_session": "s1"}
    )
    assert status == 500
    payload = json.loads(body)
    assert payload["code"] == "INTERNAL_ERROR"
    assert payload["retryable"] is True
    assert "INTERNAL_SECRET" not in body.decode("utf-8")


def test_project_http_persists_obs_manager_and_website():
    r = routes()
    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "name": "Project One",
            "obs_responsible_manager": "Dana Whitfield",
            "website_url": "https://example.com/p1",
            "expected_revision": 0,
        }).encode(),
    )
    assert status == 200
    project = json.loads(body)["project"]
    assert project["obs_responsible_manager"] == "Dana Whitfield"
    assert project["website_url"] == "https://example.com/p1"

    status, _, body = r.handle(
        "GET", "/api/projects/p1", cookies={"cp_session": "s1"}
    )
    stored = json.loads(body)["project"]
    assert stored["obs_responsible_manager"] == "Dana Whitfield"
    assert stored["website_url"] == "https://example.com/p1"

    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({
            "name": "Project One",
            "website_url": "javascript:alert(1)",
            "expected_revision": 1,
        }).encode(),
    )
    assert status == 400
    assert json.loads(body)["code"] == "PROJECT_WEBSITE_URL_INVALID"


def test_project_http_checkout_and_checkin_round_trip():
    r = routes()
    status, _, body = r.handle(
        "POST", "/api/projects/p1/checkout",
        cookies={"cp_session": "s1"},
        body=json.dumps({"checked_out": True, "expected_revision": 0}).encode(),
    )
    assert status == 200
    project = json.loads(body)["project"]
    assert project["checkout_state"] == "checked_out"
    assert project["checked_out_by"] == "u1"
    assert project["settings_revision"] == 1

    status, _, body = r.handle(
        "GET", "/api/projects/p1", cookies={"cp_session": "s1"}
    )
    stored = json.loads(body)["project"]
    assert stored["checkout_state"] == "checked_out"
    assert stored["checked_out_at"]

    status, _, body = r.handle(
        "POST", "/api/projects/p1/checkout",
        cookies={"cp_session": "s1"},
        body=json.dumps({"checked_out": False, "expected_revision": 1}).encode(),
    )
    assert status == 200
    project = json.loads(body)["project"]
    assert project["checkout_state"] == "checked_in"
    assert project["checked_out_by"] == ""
    assert project["settings_revision"] == 2

    # Releasing an already released lease is idempotent.
    status, _, body = r.handle(
        "POST", "/api/projects/p1/checkout",
        cookies={"cp_session": "s1"},
        body=json.dumps({"checked_out": False, "expected_revision": 2}).encode(),
    )
    assert status == 200
    assert json.loads(body)["project"]["settings_revision"] == 2


def test_project_http_rejects_edits_held_by_another_user():
    r = routes()
    repository = r._api._service._projects
    repository.items["p1"] = ProjectSummary(
        "p1", "t1", "Project One", 2,
        checkout_state="checked_out",
        checked_out_by="u2",
        checked_out_at="2026-09-30T07:00:00+00:00",
    )
    status, _, body = r.handle(
        "PATCH", "/api/projects/p1",
        cookies={"cp_session": "s1"},
        body=json.dumps({"name": "Blocked", "expected_revision": 0}).encode(),
    )
    assert status == 409
    assert json.loads(body)["code"] == "PROJECT_CHECKED_OUT_BY_OTHER"

    status, _, body = r.handle(
        "POST", "/api/projects/p1/checkout",
        cookies={"cp_session": "s1"},
        body=json.dumps({"checked_out": False, "expected_revision": 0}).encode(),
    )
    assert status == 409
    assert json.loads(body)["code"] == "PROJECT_CHECKOUT_CONFLICT"
