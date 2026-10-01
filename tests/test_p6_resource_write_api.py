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
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
    SQLiteP6ResourceAssignmentPeriodRepository,
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
    roles = frozenset({"viewer", "editor"}) if writer else frozenset({"viewer"})
    return AuthorizationContext(tenant, project, "writer" if writer else "reader", roles)


def build_api():
    connection = sqlite3.connect(":memory:")
    manager = TransactionManager(connection)
    repository = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    service = P6ResourceAssignmentPeriodApplicationService(repository, manager)
    return connection, repository, P6ResourceWriteAPI(service, default_project_policy())


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
