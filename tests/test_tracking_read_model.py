from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_resource_assignment_repository import P6ResourceAssignment
from construction_pm.p6_resource_master_repository import P6Resource
from construction_pm.scheduling.activity import ActivityStatus
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.tracking_read_model import (
    TRACKING_READ_MODEL_VERSION,
    TrackingReadAPI,
    TrackingReadModelError,
    TrackingReadModelService,
    TrackingRequest,
    TrackingSources,
)
from construction_pm.wbs_master_repository import WBSMaster, WBSParentKind

NOW = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
SCOPE = BackendScope("t1", "p1", 7)
AUTH = AuthorizationContext("t1", "p1", "u1", frozenset({"planner"}))
FACTS = {
    "calculation_run_identity": "run-abc",
    "project_finish": "2026-02-06",
    "activity_count": 3,
    "diagnostics": [],
    "activities": {
        "A1": {
            "start": "2026-01-05",
            "finish": "2026-01-09",
            "early_start": "2026-01-05",
            "early_finish": "2026-01-09",
            "late_start": "2026-01-05",
            "late_finish": "2026-01-09",
            "total_float": 0,
            "free_float": 0,
            "critical": True,
            "float_path": 1,
            "float_path_order": 1,
            "duration": 5,
            "percent_complete": 100,
            "status": "Completed",
        },
        "A2": {
            "start": "2026-01-08",
            "finish": "2026-01-16",
            "early_start": "2026-01-08",
            "early_finish": "2026-01-16",
            "late_start": "2026-01-12",
            "late_finish": "2026-01-20",
            "total_float": 3,
            "free_float": 1,
            "critical": False,
            "float_path": 2,
            "float_path_order": 1,
            "duration": 7,
            "percent_complete": 40,
            "status": "In Progress",
        },
        "A3": {
            "start": "2026-01-20",
            "finish": "2026-02-06",
            "early_start": "2026-01-20",
            "early_finish": "2026-02-06",
            "late_start": "2026-01-20",
            "late_finish": "2026-02-06",
            "total_float": 10,
            "free_float": 10,
            "critical": False,
            "float_path": 3,
            "float_path_order": 1,
            "duration": 14,
            "percent_complete": 0,
            "status": "Not Started",
        },
    },
}


def _activity(activity_id, name, wbs_id, planned_finish=None, status=ActivityStatus.NOT_STARTED):
    return ActivityMaster(
        scope=SCOPE,
        activity_id=activity_id,
        duration_value=Decimal("5"),
        duration_unit=DurationUnit.WORKING_DAY,
        name=name,
        wbs_id=wbs_id,
        planned_finish=planned_finish,
        status=status,
    )


class ActivityRepository:
    def list(self, scope):
        return (
            _activity(
                "A1",
                "Foundations",
                "W1",
                planned_finish=date(2026, 1, 8),
                status=ActivityStatus.COMPLETED,
            ),
            _activity(
                "A2",
                "Superstructure",
                "W1",
                planned_finish=date(2026, 1, 16),
                status=ActivityStatus.IN_PROGRESS,
            ),
            _activity("A3", "Finishes", "W2"),
        )

    def get(self, scope, activity_id):
        return next((item for item in self.list(scope) if item.activity_id == activity_id), None)


class WBSRepository:
    def list(self, scope):
        return (
            WBSMaster(SCOPE, "W1", WBSParentKind.PROJECT, None, "1.1", "Structure", 0),
            WBSMaster(SCOPE, "W2", WBSParentKind.PROJECT, None, "1.2", "Finishes", 1),
        )


class AssignmentRepository:
    def list(self, scope, activity_id=None, resource_id=None):
        return (
            P6ResourceAssignment(
                scope=SCOPE,
                assignment_id="AS1",
                activity_id="A1",
                resource_id="R1",
                units=Decimal("0.1"),
                planned_cost=Decimal("100.10"),
                actual_cost=Decimal("50.05"),
                remaining_cost=Decimal("50.05"),
                currency="USD",
            ),
            P6ResourceAssignment(
                scope=SCOPE,
                assignment_id="AS2",
                activity_id="A2",
                resource_id="R1",
                units=Decimal("0.2"),
                planned_cost=Decimal("200.20"),
                actual_cost=Decimal("0"),
                remaining_cost=Decimal("200.20"),
                currency="USD",
            ),
        )


class ResourceRepository:
    def list(self, tenant_id, project_id, project_revision):
        return (
            P6Resource(
                "t1", "p1", 7, "R1", "Steel crew", resource_type="labor", unit_of_measure="ton"
            ),
        )


def _service(*, with_resources=True):
    return TrackingReadModelService(
        schedule_facts_provider=lambda scope, auth: dict(FACTS),
        sources=TrackingSources(
            activity_repository=ActivityRepository(),
            wbs_repository=WBSRepository(),
            resource_assignment_repository=AssignmentRepository() if with_resources else None,
            resource_repository=ResourceRepository() if with_resources else None,
        ),
    )


def test_tracking_projects_authoritative_rows_and_summary() -> None:
    model = _service().build(SCOPE, auth_context=AUTH, request=TrackingRequest())
    assert model["contract_version"] == TRACKING_READ_MODEL_VERSION
    assert model["source"]["calculation_run_identity"] == "run-abc"
    assert model["source"]["authoritative"] is True
    assert [row["activity_id"] for row in model["rows"]] == ["A1", "A2", "A3"]
    first = model["rows"][0]
    assert first["name"] == "Foundations"
    assert first["wbs_code"] == "1.1"
    assert first["critical"] is True
    assert first["finish_variance_days"] == 1
    assert model["rows"][1]["finish_variance_days"] == 0
    assert model["rows"][2]["finish_variance_days"] is None
    summary = model["summary"]
    assert summary["activity_count"] == 3
    assert summary["completed_count"] == 1
    assert summary["in_progress_count"] == 1
    assert summary["not_started_count"] == 1
    assert summary["critical_count"] == 1
    assert summary["mean_percent_complete"] == "46.66666666666666666666666667"
    assert summary["project_finish"] == "2026-02-06"


def test_tracking_bar_chart_and_profile_bucket_by_finish_and_start() -> None:
    model = _service().build(SCOPE, auth_context=AUTH, request=TrackingRequest(scale="week"))
    assert model["bar_chart"] == [
        {"bucket": "2026-01-05", "total": 1, "not_started": 0, "in_progress": 0, "completed": 1, "critical": 1},
        {"bucket": "2026-01-12", "total": 1, "not_started": 0, "in_progress": 1, "completed": 0, "critical": 0},
        {"bucket": "2026-02-02", "total": 1, "not_started": 1, "in_progress": 0, "completed": 0, "critical": 0},
    ]
    assert model["profile"] == [
        {"bucket": "2026-01-05", "activity_count": 2, "duration": "12"},
        {"bucket": "2026-01-19", "activity_count": 1, "duration": "14"},
    ]


def test_tracking_groups_sorting_and_scale_options() -> None:
    model = _service().build(
        SCOPE,
        auth_context=AUTH,
        request=TrackingRequest(group_by="wbs", sort="finish", direction="desc", scale="month"),
    )
    assert model["layout"] == {
        "scale": "month",
        "group_by": "wbs",
        "sort": "finish",
        "direction": "desc",
    }
    assert [row["activity_id"] for row in model["rows"]] == ["A3", "A2", "A1"]
    assert model["groups"] == [
        {"group": "1.1", "activity_count": 2, "critical_count": 1, "completed_count": 1},
        {"group": "1.2", "activity_count": 1, "critical_count": 0, "completed_count": 0},
    ]
    assert [bucket["bucket"] for bucket in model["bar_chart"]] == ["2026-01-01", "2026-02-01"]


def test_tracking_resource_analysis_sums_decimal_units_exactly() -> None:
    model = _service().build(SCOPE, auth_context=AUTH, request=TrackingRequest())
    analysis = model["resource_analysis"]
    assert analysis["status"] == "available"
    assert analysis["basis"] == "persisted_assignments"
    resource = analysis["resources"][0]
    assert resource["resource_id"] == "R1"
    assert resource["resource_name"] == "Steel crew"
    assert resource["activity_count"] == 2
    assert resource["assignment_count"] == 2
    assert resource["planned_units"] == "0.3"
    assert resource["planned_cost"] == "300.30"
    assert resource["actual_cost"] == "50.05"
    assert analysis["totals"]["planned_units"] == "0.3"
    assert analysis["totals"]["planned_cost"] == "300.30"


def test_tracking_without_resource_source_reports_an_explicit_warning() -> None:
    model = _service(with_resources=False).build(
        SCOPE, auth_context=AUTH, request=TrackingRequest()
    )
    assert model["resource_analysis"]["status"] == "unavailable"
    assert model["warnings"] == [{"code": "TRACKING_RESOURCE_SOURCE_UNAVAILABLE"}]
    assert model["resource_analysis"]["resources"] == []


def test_tracking_fails_closed_without_a_published_schedule() -> None:
    service = TrackingReadModelService(
        schedule_facts_provider=lambda scope, auth: None,
        sources=TrackingSources(activity_repository=ActivityRepository()),
    )
    with pytest.raises(TrackingReadModelError) as excinfo:
        service.build(SCOPE, auth_context=AUTH, request=TrackingRequest())
    assert str(excinfo.value) == "TRACKING_SCHEDULE_NOT_PUBLISHED"


def test_tracking_rejects_invalid_layout_and_scope() -> None:
    with pytest.raises(TrackingReadModelError):
        _service().build(
            SCOPE, auth_context=AUTH, request=TrackingRequest(scale="quarter")
        )
    other = AuthorizationContext("t2", "p1", "u1", frozenset({"planner"}))
    with pytest.raises(TrackingReadModelError):
        _service().build(SCOPE, auth_context=other, request=TrackingRequest())


# --- HTTP -------------------------------------------------------------------


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("p1", tenant_id, "Project One", 7),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 7)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def _router(roles=frozenset({"planner"})):
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        tracking_read_api=TrackingReadAPI(_service(), default_project_policy()),
    )


def _call(router, path, session="s1"):
    status, _, raw = router.handle("GET", path, cookies={"cp_session": session})
    return status, json.loads(raw)


def test_http_tracking_read_returns_the_projection() -> None:
    router = _router()
    status, body = _call(router, "/api/projects/p1/tracking/read?scale=week&group_by=wbs")
    assert status == 200, body
    assert body["contract_version"] == TRACKING_READ_MODEL_VERSION
    assert body["scope"] == {"tenant_id": "t1", "project_id": "p1", "project_revision": 7}
    assert body["summary"]["activity_count"] == 3
    assert body["resource_analysis"]["resources"][0]["planned_units"] == "0.3"


def test_http_tracking_read_is_permission_and_scope_guarded() -> None:
    router = _router()
    status, body = _call(router, "/api/projects/other/tracking/read")
    assert status == 403
    assert body["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"

    status, body = _call(router, "/api/projects/p1/tracking/read?scale=quarter")
    assert status == 400
    assert body["code"] == "INVALID_TRACKING_SCALE"


def test_http_tracking_read_reports_unpublished_schedule_as_conflict() -> None:
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"planner"}), NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        tracking_read_api=TrackingReadAPI(
            TrackingReadModelService(
                schedule_facts_provider=lambda scope, auth: None,
                sources=TrackingSources(activity_repository=ActivityRepository()),
            ),
            default_project_policy(),
        ),
    )
    status, body = _call(router, "/api/projects/p1/tracking/read")
    assert status == 409
    assert body["code"] == "TRACKING_SCHEDULE_NOT_PUBLISHED"
