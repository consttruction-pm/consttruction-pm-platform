import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest

from construction_pm.application.authorization import AuthorizationContext, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_leveling_read_adapter import build_scheduler_leveling_input
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.resources.calendar import ResourceCalendar
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.resource_leveling import LevelingActivity, ResourceLevelingOptions


class TransactionManager:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def transaction(self):
        yield


def auth(tenant="tenant-a", project="project-a"):
    return AuthorizationContext(tenant, project, "reader", frozenset({"viewer"}))


def build_api():
    connection = sqlite3.connect(":memory:")
    manager = TransactionManager(connection)
    assignment_repo = SQLiteP6ResourceAssignmentRepository(connection)
    period_repo = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    spread_repo = SQLiteP6ResourceSpreadRepository(connection)
    api = P6ResourceReadAPI(
        P6ResourceAssignmentApplicationService(assignment_repo, manager),
        P6ResourceAssignmentPeriodApplicationService(period_repo, manager),
        P6ResourceSpreadApplicationService(spread_repo, manager),
        default_project_policy(),
    )
    return api, assignment_repo, period_repo


def test_adapter_maps_authoritative_demand_and_calendar_capacity():
    api, assignment_repo, period_repo = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)
    assignment_repo.upsert(
        P6ResourceAssignment(
            scope, "a-1", "activity-1", "resource-1",
            units=Decimal("8"), calendar_id="calendar-1",
        )
    )
    period_repo.upsert(
        P6ResourceAssignmentPeriodValue(
            scope, "a-1", "activity-1", "resource-1",
            "2026-10-02", Decimal("6.25"), Decimal("0"),
        )
    )

    activities = (
        LevelingActivity("activity-1", date(2026, 10, 2), date(2026, 10, 3), 2),
    )
    result = build_scheduler_leveling_input(
        read_api=api,
        scope=scope,
        auth_context=auth(),
        forward_activities=activities,
        backward_activities=activities,
        calendars={
            "calendar-1": ResourceCalendar(
                "calendar-1", frozenset({0, 1, 2, 3, 4}), Decimal("8.5")
            )
        },
        periods=(date(2026, 10, 2),),
        options=ResourceLevelingOptions(),
    )

    assert isinstance(result, SchedulerLevelingInput)
    assert result.forward_activities[0].resource_demands[0].units == Decimal("6.25")
    assert result.forward_activities[0].resource_demands[0].activity_id == "activity-1"
    assert result.capacities == (
        result.capacities[0],
    )
    assert result.capacities[0].resource_id == "resource-1"
    assert result.capacities[0].period == date(2026, 10, 2)
    assert result.capacities[0].units == Decimal("8.5")
    assert result.forward_activities[0].resource_demands[0].units.as_tuple() == Decimal("6.25").as_tuple()


def test_adapter_preserves_deterministic_order_and_scope():
    api, assignment_repo, period_repo = build_api()
    scope = BackendScope("tenant-a", "project-a", 9)
    for assignment_id, resource_id in (("b-2", "resource-b"), ("a-1", "resource-a")):
        assignment_repo.upsert(
            P6ResourceAssignment(
                scope, assignment_id, "activity-1", resource_id,
                units=Decimal("4"), calendar_id=f"calendar-{resource_id}",
            )
        )
    period_repo.upsert(
        P6ResourceAssignmentPeriodValue(
            scope, "b-2", "activity-1", "resource-b",
            "2026-10-02", Decimal("2"), Decimal("0"),
        )
    )
    period_repo.upsert(
        P6ResourceAssignmentPeriodValue(
            scope, "a-1", "activity-1", "resource-a",
            "2026-10-01", Decimal("1.5"), Decimal("0"),
        )
    )

    activity = LevelingActivity("activity-1", date(2026, 10, 1), date(2026, 10, 2), 0)
    result = build_scheduler_leveling_input(
        read_api=api,
        scope=scope,
        auth_context=auth(),
        forward_activities=(activity,),
        backward_activities=(activity,),
        calendars={
            "calendar-resource-a": ResourceCalendar("calendar-resource-a"),
            "calendar-resource-b": ResourceCalendar("calendar-resource-b"),
        },
        periods=(date(2026, 10, 1), date(2026, 10, 2)),
        options=ResourceLevelingOptions(),
    )

    assert [(d.period, d.resource_id, d.units) for d in result.forward_activities[0].resource_demands] == [
        (date(2026, 10, 1), "resource-a", Decimal("1.5")),
        (date(2026, 10, 2), "resource-b", Decimal("2")),
    ]
    assert [(c.resource_id, c.period) for c in result.capacities] == [
        ("resource-a", date(2026, 10, 1)),
        ("resource-a", date(2026, 10, 2)),
        ("resource-b", date(2026, 10, 1)),
        ("resource-b", date(2026, 10, 2)),
    ]
    assert result.forward_activities[0].resource_demands[0].activity_id == "activity-1"


def test_adapter_enforces_existing_read_api_authorization_boundary():
    api, assignment_repo, _ = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)
    assignment_repo.upsert(
        P6ResourceAssignment(
            scope, "a-1", "activity-1", "resource-1",
            units=Decimal("1"), calendar_id="calendar-1",
        )
    )

    with pytest.raises(Exception, match="CROSS_SCOPE_ACCESS"):
        build_scheduler_leveling_input(
            read_api=api,
            scope=scope,
            auth_context=auth("tenant-b", "project-a"),
            forward_activities=(),
            backward_activities=(),
            calendars={"calendar-1": ResourceCalendar("calendar-1")},
            periods=(date(2026, 10, 1),),
            options=ResourceLevelingOptions(),
        )
