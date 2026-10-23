import sqlite3
from contextlib import contextmanager
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
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
from construction_pm.p6_resource_write_api import (
    P6_RESOURCE_WRITE_API_VERSION,
    P6ResourceWriteAPI,
)


class TransactionManager:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def transaction(self):
        yield


def auth(tenant="tenant-a", project="project-a", *, writer=True):
    roles = frozenset({"viewer", "planner"}) if writer else frozenset({"viewer"})
    return AuthorizationContext(tenant, project, "writer" if writer else "reader", roles)


def build_api():
    connection = sqlite3.connect(":memory:")
    manager = TransactionManager(connection)
    repository = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    service = P6ResourceAssignmentPeriodApplicationService(repository, manager)
    assignment_repository = SQLiteP6ResourceAssignmentRepository(connection)
    assignment_service = P6ResourceAssignmentApplicationService(assignment_repository, manager)
    return (
        connection,
        repository,
        P6ResourceWriteAPI(
            service, default_project_policy(), assignment_service=assignment_service
        ),
    )


def value(scope, period_start="2026-10-01", units="4.25", cost="425.50"):
    return P6ResourceAssignmentPeriodValue(
        scope=scope,
        assignment_id="ra-1",
        activity_id="act-1",
        resource_id="res-1",
        period_start=period_start,
        units=Decimal(units),
        cost=Decimal(cost),
    )


def test_resource_write_api_persists_assignment_period_with_typed_contract():
    _, repository, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)

    result = api.save_assignment_period(value(scope), auth_context=auth())

    assert result["contract_version"] == P6_RESOURCE_WRITE_API_VERSION
    assert result["kind"] == "resource_assignment_period"
    assert result["scope"]["project_revision"] == 7
    assert result["period"]["units"] == Decimal("4.25")
    assert repository.get(scope, "ra-1", "2026-10-01") == value(scope)


def test_resource_write_api_allows_identical_replay_but_preserves_immutable_conflict():
    _, _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)
    item = value(scope)

    assert api.save_assignment_period(item, auth_context=auth()) == api.save_assignment_period(
        item, auth_context=auth()
    )

    with pytest.raises(ValueError, match="IMMUTABLE_RESOURCE_ASSIGNMENT_PERIOD_VALUE"):
        api.save_assignment_period(
            value(scope, units="4.50"),
            auth_context=auth(),
        )


def test_resource_write_api_enforces_scope_and_project_write():
    _, _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.save_assignment_period(
            value(scope),
            auth_context=auth("tenant-b", "project-a"),
        )

    with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
        api.save_assignment_period(
            value(scope),
            auth_context=auth(writer=False),
        )


def test_resource_write_api_preserves_revision_conflict_from_repository():
    _, _, api = build_api()
    original_scope = BackendScope("tenant-a", "project-a", 1)
    stale_scope = BackendScope("tenant-a", "project-a", 2)

    api.save_assignment_period(value(original_scope), auth_context=auth())

    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        api.save_assignment_period(value(stale_scope), auth_context=auth())



@pytest.mark.parametrize("is_driving", [True, False, None])
def test_resource_write_api_persists_and_returns_explicit_assignment_driving_status(is_driving):
    connection, _, api = build_api()
    repository = SQLiteP6ResourceAssignmentRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 7)
    item = P6ResourceAssignment(
        scope=scope,
        assignment_id=f"ra-{is_driving}",
        activity_id="act-1",
        resource_id="res-1",
        units=Decimal("8"),
        unit="hours",
        is_driving=is_driving,
        units_per_time=Decimal("2.5"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
    )

    created = api.save_assignment(item, auth_context=auth())

    assert created["contract_version"] == P6_RESOURCE_WRITE_API_VERSION
    assert created["kind"] == "resource_assignment"
    assert created["scope"]["project_revision"] == 7
    assert created["assignment"]["is_driving"] is is_driving
    assert created["assignment"]["units_per_time"] == Decimal("2.5")
    assert created["assignment"]["units_per_time_period"] == "day"
    assert created["assignment"]["hours_per_units_time_period"] == Decimal("8")
    assert repository.get(scope, item.assignment_id) == item
    assert api.save_assignment(item, auth_context=auth()) == created


def test_resource_write_api_enforces_scope_and_project_write_for_assignments():
    _, _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 1)
    item = P6ResourceAssignment(
        scope=scope, assignment_id="ra-1", activity_id="act-1",
        resource_id="res-1", is_driving=True,
    )

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        api.save_assignment(item, auth_context=auth("tenant-b", "project-a"))
    with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
        api.save_assignment(item, auth_context=auth(writer=False))
