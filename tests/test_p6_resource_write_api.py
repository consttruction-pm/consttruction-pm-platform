import sqlite3
from contextlib import contextmanager
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
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
    assignment_repository = SQLiteP6ResourceAssignmentRepository(connection)
    service = P6ResourceAssignmentPeriodApplicationService(repository, manager)
    assignment_service = P6ResourceAssignmentApplicationService(assignment_repository, manager)
    return connection, repository, P6ResourceWriteAPI(
        service, default_project_policy(), assignment_service=assignment_service
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



def test_resource_write_api_persists_explicit_driving_status_and_units_per_time():
    connection, _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)
    item = P6ResourceAssignment(
        scope=scope,
        assignment_id="ra-driving",
        activity_id="act-1",
        resource_id="res-1",
        units=Decimal("16"),
        remaining_units=Decimal("12"),
        unit="labor-unit",
        calendar_id="resource-calendar",
        calendar_version="v4",
        is_driving=True,
        units_per_time=Decimal("4"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
    )

    result = api.save_assignment(item, auth_context=auth())

    assert result["contract_version"] == P6_RESOURCE_WRITE_API_VERSION
    assert result["kind"] == "resource_assignment"
    assert result["assignment"]["is_driving"] is True
    assert result["assignment"]["units_per_time"] == Decimal("4")
    assert result["assignment"]["units_per_time_period"] == "day"
    assert result["assignment"]["hours_per_units_time_period"] == Decimal("8")
    assert api.assignment_service.read(scope, "ra-driving") == item
    connection.close()


def test_resource_write_api_assignment_requires_explicit_writer_and_preserves_unknown_legacy_value():
    _, _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)
    legacy = P6ResourceAssignment(
        scope=scope,
        assignment_id="ra-legacy",
        activity_id="act-1",
        resource_id="res-1",
        calendar_id="resource-calendar",
        calendar_version="v1",
        is_driving=None,
    )

    with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
        api.save_assignment(legacy, auth_context=auth(writer=False))

    response = api.save_assignment(legacy, auth_context=auth())
    assert response["assignment"]["is_driving"] is None


def test_resource_write_api_assignment_rejects_invalid_driving_flag():
    _, _, api = build_api()
    invalid = P6ResourceAssignment(
        scope=BackendScope("tenant-a", "project-a", 1),
        assignment_id="ra-invalid",
        activity_id="act-1",
        resource_id="res-1",
        is_driving="false",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="INVALID_IS_DRIVING"):
        api.save_assignment(invalid, auth_context=auth())

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

class _ActivityLookup:
    def __init__(self, activities):
        self.activities = activities

    def get(self, scope, activity_id):
        return self.activities.get(activity_id)


class _WbsScopedWritePolicy:
    def __init__(self):
        self.allowed_permissions = {
            Permission.P6_ACTIVITY_ADMIN,
            Permission.P6_EDIT_PERIOD_PERFORMANCE,
        }

    def is_allowed(self, context, permission):
        # A broad project grant must not override a WBS-scoped denial.
        return True

    def is_allowed_for_wbs(self, context, permission, wbs_id):
        return wbs_id == "wbs-authorized" and permission in self.allowed_permissions



def test_resource_planning_assignment_requires_its_own_v26_privilege_and_wbs_scope():
    connection, _, legacy_api = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)
    policy = _WbsScopedWritePolicy()
    activity_repository = _ActivityLookup({
        "act-authorized": type("Activity", (), {"wbs_id": "wbs-authorized"})(),
        "act-restricted": type("Activity", (), {"wbs_id": "wbs-restricted"})(),
    })
    api = P6ResourceWriteAPI(
        legacy_api.period_service,
        policy,
        assignment_service=legacy_api.assignment_service,
        activity_repository=activity_repository,
    )
    assignment = P6ResourceAssignment(
        scope, "ra-planning-authorized", "act-authorized", "resource-planning-1"
    )

    # Add/Edit Activities is not the separate Resources > Planning privilege.
    with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
        api.create_resource_planning_assignment(assignment, auth_context=auth())

    policy.allowed_permissions.add(Permission.P6_RESOURCE_PLANNING_ASSIGNMENT_ADMIN)
    created = api.create_resource_planning_assignment(assignment, auth_context=auth())
    assert created["kind"] == "resource_assignment"
    assert created["assignment"]["assignment_id"] == assignment.assignment_id

    restricted = P6ResourceAssignment(
        scope, "ra-planning-restricted", "act-restricted", "resource-planning-1"
    )
    with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
        api.create_resource_planning_assignment(restricted, auth_context=auth())
    connection.close()

def test_resource_write_api_uses_activity_wbs_and_v26_privilege_per_operation():
    connection, _, legacy_api = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)
    policy = _WbsScopedWritePolicy()
    activity_repository = _ActivityLookup({
        "act-authorized": type("Activity", (), {"wbs_id": "wbs-authorized"})(),
        "act-restricted": type("Activity", (), {"wbs_id": "wbs-restricted"})(),
    })
    api = P6ResourceWriteAPI(
        legacy_api.period_service,
        policy,
        assignment_service=legacy_api.assignment_service,
        activity_repository=activity_repository,
    )

    allowed_assignment = P6ResourceAssignment(
        scope, "ra-authorized", "act-authorized", "resource-1"
    )
    assert api.save_assignment(allowed_assignment, auth_context=auth())["kind"] == "resource_assignment"
    with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
        api.save_assignment(
            P6ResourceAssignment(scope, "ra-restricted", "act-restricted", "resource-1"),
            auth_context=auth(),
        )

    allowed_period = P6ResourceAssignmentPeriodValue(
        scope, "ra-authorized", "act-authorized", "resource-1",
        "2026-10-01", Decimal("4.25"), Decimal("425.50"),
    )
    assert api.save_assignment_period(allowed_period, auth_context=auth())["kind"] == "resource_assignment_period"
    denied_period = P6ResourceAssignmentPeriodValue(
        scope, "ra-restricted", "act-restricted", "resource-1",
        "2026-10-01", Decimal("4.25"), Decimal("425.50"),
    )
    with pytest.raises(AuthorizationError, match="RESOURCE_WRITE_NOT_AUTHORIZED"):
        api.save_assignment_period(denied_period, auth_context=auth())

    # Profile-backed WBS authorization must fail closed when activity lookup
    # was not wired; it cannot silently degrade to project-wide authorization.
    with pytest.raises(ValueError, match="RESOURCE_ACTIVITY_SCOPE_NOT_CONFIGURED"):
        P6ResourceWriteAPI(
            legacy_api.period_service, policy,
            assignment_service=legacy_api.assignment_service,
        )
    connection.close()

