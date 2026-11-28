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
from construction_pm.p6_resource_master_repository import (
    P6Resource,
    SQLiteP6ResourceRepository,
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
    resources = SQLiteP6ResourceRepository(connection)
    resources.save(
        P6Resource(
            tenant_id="tenant-a",
            project_id="project-a",
            project_revision=1,
            resource_id="res-1",
            name="Crew",
        )
    )
    return connection, repository, P6ResourceWriteAPI(
        service,
        default_project_policy(),
        resources,
        assignment_service=assignment_service,
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


def _assignment(scope, resource_id, assignment_id="ra-dict"):
    return P6ResourceAssignment(
        scope=scope,
        assignment_id=assignment_id,
        activity_id="act-1",
        resource_id=resource_id,
    )


def test_resource_write_api_rejects_an_unknown_or_foreign_resource_id():
    _, _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)

    with pytest.raises(ValueError, match="RESOURCE_NOT_FOUND"):
        api.save_assignment(
            _assignment(scope, "res-missing"), auth_context=auth()
        )

    api.resource_repository.save(
        P6Resource(
            tenant_id="tenant-b",
            project_id="project-a",
            project_revision=1,
            resource_id="res-foreign",
            name="Foreign crew",
        )
    )
    with pytest.raises(ValueError, match="RESOURCE_NOT_FOUND"):
        api.save_assignment(
            _assignment(scope, "res-foreign"), auth_context=auth()
        )


def test_resource_write_api_rejects_an_inactive_resource_but_keeps_legacy_assignments():
    _, _, api = build_api()
    scope = BackendScope("tenant-a", "project-a", 7)
    legacy = _assignment(scope, "res-1", assignment_id="ra-legacy")
    api.save_assignment(legacy, auth_context=auth())

    api.resource_repository.save(
        P6Resource(
            tenant_id="tenant-a",
            project_id="project-a",
            project_revision=1,
            resource_id="res-1",
            name="Crew",
            is_active=False,
        ),
        expected_revision=1,
    )

    with pytest.raises(ValueError, match="RESOURCE_INACTIVE"):
        api.save_assignment(
            _assignment(scope, "res-1", assignment_id="ra-new"), auth_context=auth()
        )
    # The assignment written while the resource was active is still readable.
    assert api.assignment_service.read(scope, "ra-legacy") == legacy


def test_resource_write_api_dictionary_check_resolves_the_identity_across_revisions():
    _, _, api = build_api()
    # res-1 is stamped at revision 1; an assignment written at the current
    # revision 7 must still resolve the same identity (one row per resource).
    result = api.save_assignment(
        _assignment(BackendScope("tenant-a", "project-a", 7), "res-1"),
        auth_context=auth(),
    )
    assert result["assignment"]["resource_id"] == "res-1"
