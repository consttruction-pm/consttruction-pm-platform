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
        unit="hours", currency="USD",
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
