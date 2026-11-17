import sqlite3
from contextlib import contextmanager
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_master_repository import P6Resource, SQLiteP6ResourceRepository
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    P6ResourceSpreadBucket,
    SQLiteP6ResourceSpreadRepository,
)


class TransactionManager:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def transaction(self):
        yield


def auth(tenant="tenant-a", project="project-a"):
    from construction_pm.application.authorization import AuthorizationContext
    return AuthorizationContext(tenant, project, "reader", frozenset({"viewer"}))


def build_api():
    connection = sqlite3.connect(":memory:")
    manager = TransactionManager(connection)
    assignment_repo = SQLiteP6ResourceAssignmentRepository(connection)
    period_repo = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    spread_repo = SQLiteP6ResourceSpreadRepository(connection)
    return (
        connection,
        P6ResourceReadAPI(
            P6ResourceAssignmentApplicationService(assignment_repo, manager),
            P6ResourceAssignmentPeriodApplicationService(period_repo, manager),
            P6ResourceSpreadApplicationService(spread_repo, manager),
            default_project_policy(),
        ),
        assignment_repo,
        period_repo,
        spread_repo,
    )


def test_resource_read_api_exposes_typed_assignment_period_and_spread_data():
    _, api, assignment_repo, period_repo, spread_repo = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)

    assignment = P6ResourceAssignment(
        scope, "a-1", "activity-1", "resource-1",
        units=Decimal("8.50"), planned_cost=Decimal("850.25"),
        unit="hours", currency="USD", calendar_id="calendar-1",
        calendar_version="cal-v7",
        is_driving=True,
        units_per_time=Decimal("2.5"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
    )
    period = P6ResourceAssignmentPeriodValue(
        scope, "a-1", "activity-1", "resource-1",
        "2026-10-01", Decimal("4.25"), Decimal("425.125"),
    )
    spread = P6ResourceSpreadBucket(
        scope=scope, spread_id="s-1", resource_id="resource-1",
        period_id="2026-10", period_start="2026-10-01", period_end="2026-10-31",
        spread_type="PLANNED", metric="UNITS", value=Decimal("4.25"), unit="hours",
    )
    assignment_repo.upsert(assignment)
    period_repo.upsert(period)
    spread_repo.upsert(spread)

    result = api.get_assignment(scope, "a-1", auth_context=auth())
    assert result["scope"]["project_revision"] == 7
    assert result["assignment"]["units"] == Decimal("8.50")
    assert result["assignment"]["calendar_id"] == "calendar-1"
    assert result["assignment"]["calendar_version"] == "cal-v7"
    assert result["assignment"]["is_driving"] is True
    assert result["assignment"]["units_per_time"] == Decimal("2.5")
    assert result["assignment"]["units_per_time_period"] == "day"
    assert result["assignment"]["hours_per_units_time_period"] == Decimal("8")

    periods = api.list_assignment_periods(scope, assignment_id="a-1", auth_context=auth())
    assert periods[0]["period"]["cost"] == Decimal("425.125")

    spreads = api.list_spreads(scope, spread_id="s-1", auth_context=auth())
    assert spreads[0]["spread"]["value"] == Decimal("4.25")


def test_resource_read_api_preserves_scope_and_deterministic_ordering():
    _, api, assignment_repo, period_repo, _ = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)
    for assignment_id in ("b-2", "a-1"):
        assignment_repo.upsert(
            P6ResourceAssignment(scope, assignment_id, "activity-1", "resource-1")
        )
    period_repo.upsert(
        P6ResourceAssignmentPeriodValue(
            scope, "a-1", "activity-1", "resource-1",
            "2026-10-02", Decimal("2"), Decimal("20"),
        )
    )
    period_repo.upsert(
        P6ResourceAssignmentPeriodValue(
            scope, "a-1", "activity-1", "resource-1",
            "2026-10-01", Decimal("1"), Decimal("10"),
        )
    )

    assignments = api.list_assignments(scope, auth_context=auth())
    assert [item["assignment"]["assignment_id"] for item in assignments] == ["a-1", "b-2"]
    periods = api.list_assignment_periods(scope, assignment_id="a-1", auth_context=auth())
    assert [item["period"]["period_start"] for item in periods] == ["2026-10-01", "2026-10-02"]
    assert api.get_assignment(BackendScope("tenant-b", "project-a", 1), "a-1", auth_context=auth("tenant-b")) is None


def test_resource_read_api_rejects_cross_scope_and_non_reader():
    _, api, *_ = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)
    from construction_pm.application.authorization import AuthorizationContext
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.list_assignments(scope, auth_context=auth("tenant-b"))
    with pytest.raises(AuthorizationError, match="RESOURCE_READ_NOT_AUTHORIZED"):
        api.list_assignments(
            scope,
            auth_context=AuthorizationContext("tenant-a", "project-a", "writer", frozenset()),
        )


class SelectedResourcePolicy:
    def is_allowed(self, context, permission):
        return True

    def can_access_resource(self, context, resource_id, ancestor_resource_ids):
        return "resource-1" in ancestor_resource_ids


def test_resource_assignment_reads_apply_global_resource_access_before_serialization():
    connection, base_api, assignment_repo, _, _ = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)
    resource_repo = SQLiteP6ResourceRepository(connection)
    resource_repo.save(P6Resource("tenant-a", "project-a", 7, "resource-1", "Selected"))
    resource_repo.save(P6Resource("tenant-a", "project-a", 7, "resource-2", "Restricted"))
    for assignment_id, resource_id in (("a-1", "resource-1"), ("a-2", "resource-2")):
        assignment_repo.upsert(P6ResourceAssignment(scope, assignment_id, "activity-1", resource_id))

    restricted = P6ResourceReadAPI(
        base_api.assignment_service, base_api.period_service, base_api.spread_service,
        SelectedResourcePolicy(), resource_repository=resource_repo,
    )
    result = restricted.list_assignments(scope, auth_context=auth())
    assert [item["assignment"]["assignment_id"] for item in result] == ["a-1"]
    assert restricted.get_assignment(scope, "a-2", auth_context=auth()) is None
