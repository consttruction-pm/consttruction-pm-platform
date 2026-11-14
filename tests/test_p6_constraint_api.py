from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import sqlite3

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.constraint_master_repository import (
    ConstraintMaster,
    SQLiteConstraintMasterRepository,
)
from construction_pm.p6_constraint_api import P6_CONSTRAINT_API_VERSION, P6ConstraintAPI
from construction_pm.project_checkout import ProjectCheckoutConflict
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.scheduling.time_duration import DurationUnit


TENANT = "tenant-constraint"
PROJECT = "project-constraint"
OWNER = "user-owner"
OTHER = "user-other"


@dataclass(frozen=True)
class Lease:
    holder: str | None

    def checked_out_by(self, scope: BackendScope) -> str | None:
        return self.holder


def scope(revision: int = 2) -> BackendScope:
    return BackendScope(TENANT, PROJECT, revision)


def auth(user: str = OWNER, tenant: str = TENANT, project: str = PROJECT):
    return AuthorizationContext(tenant, project, user, frozenset({"planner"}))


def constraint(
    *,
    constraint_id: str = "c-1",
    activity_id: str = "A-1",
    kind: ConstraintType = ConstraintType.START_NO_EARLIER_THAN,
    day: date = date(2026, 10, 20),
    revision: int = 0,
) -> ConstraintMaster:
    return ConstraintMaster(
        scope=scope(),
        constraint_id=constraint_id,
        activity_id=activity_id,
        constraint_type=kind,
        constraint_date=day,
        record_revision=revision,
    )


def activities(connection: sqlite3.Connection) -> SQLiteActivityMasterRepository:
    repository = SQLiteActivityMasterRepository(connection)
    repository.save(
        ActivityMaster(
            scope=scope(),
            activity_id="A-1",
            duration_value=Decimal("5"),
            duration_unit=DurationUnit.WORKING_DAY,
            name="Earthworks",
        )
    )
    return repository


def api(connection: sqlite3.Connection, *, with_activity: bool = True) -> P6ConstraintAPI:
    return P6ConstraintAPI(
        SQLiteConstraintMasterRepository(connection),
        default_project_policy(),
        activities(connection) if with_activity else None,
        checkout_lease=Lease(OWNER),
    )


def test_p6_constraint_api_round_trip_preserves_typed_constraint_values():
    service = api(sqlite3.connect(":memory:"))
    created = service.create(constraint(), auth_context=auth())
    assert created["contract_version"] == P6_CONSTRAINT_API_VERSION
    assert created["kind"] == "p6_constraint"
    assert created["constraint"] == {
        "constraint_id": "c-1",
        "activity_id": "A-1",
        "constraint_type": "START_NO_EARLIER_THAN",
        "constraint_date": "2026-10-20",
        "record_revision": 1,
    }
    assert service.get(scope(), "c-1", auth_context=auth()) == created
    assert service.list(scope(), auth_context=auth()) == (created,)


def test_p6_constraint_api_enforces_scope_permission_and_checkout_lease():
    service = api(sqlite3.connect(":memory:"))
    service.create(constraint(), auth_context=auth())

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.get(scope(), "c-1", auth_context=auth(tenant="other"))
    with pytest.raises(AuthorizationError):
        service.create(
            constraint(constraint_id="c-2"),
            auth_context=AuthorizationContext(
                TENANT, PROJECT, OTHER, frozenset({"viewer"})
            ),
        )
    with pytest.raises(ProjectCheckoutConflict):
        service.create(constraint(constraint_id="c-3"), auth_context=auth(user=OTHER))


def test_p6_constraint_api_requires_optimistic_revision_for_update_and_delete():
    service = api(sqlite3.connect(":memory:"))
    service.create(constraint(), auth_context=auth())

    updated = service.update(
        constraint(kind=ConstraintType.MANDATORY_FINISH, revision=1),
        expected_revision=1,
        auth_context=auth(),
    )
    assert updated["constraint"]["constraint_type"] == "MANDATORY_FINISH"
    assert updated["constraint"]["record_revision"] == 2

    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        service.update(constraint(revision=1), expected_revision=1, auth_context=auth())

    deleted = service.delete(scope(), "c-1", expected_revision=2, auth_context=auth())
    assert deleted["kind"] == "p6_constraint_delete"
    assert deleted["deleted"] is True
    assert service.list(scope(), auth_context=auth()) == ()

    with pytest.raises(ValueError, match="CONSTRAINT_NOT_FOUND"):
        service.delete(scope(), "c-1", expected_revision=2, auth_context=auth())


def test_p6_constraint_api_rejects_unknown_and_duplicate_constraints():
    service = api(sqlite3.connect(":memory:"))
    service.create(constraint(), auth_context=auth())

    with pytest.raises(ValueError, match="DUPLICATE_CONSTRAINT_TYPE"):
        service.create(constraint(constraint_id="c-2"), auth_context=auth())

    with pytest.raises(ValueError, match="ACTIVITY_NOT_FOUND_OR_SCOPE_MISMATCH"):
        service.create(
            constraint(constraint_id="c-3", activity_id="A-404"),
            auth_context=auth(),
        )


def test_p6_constraint_api_rejects_constraints_on_derived_activity_types():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteActivityMasterRepository(connection)
    from construction_pm.scheduling.activity import ActivityType

    repository.save(
        ActivityMaster(
            scope=scope(),
            activity_id="LOE-1",
            duration_value=Decimal("0"),
            duration_unit=DurationUnit.WORKING_DAY,
            name="Level of effort",
            activity_type=ActivityType.LEVEL_OF_EFFORT,
            original_duration=0,
            remaining_duration=0,
        )
    )
    service = P6ConstraintAPI(
        SQLiteConstraintMasterRepository(connection),
        default_project_policy(),
        repository,
        checkout_lease=Lease(OWNER),
    )
    with pytest.raises(ValueError, match="CONSTRAINT_ACTIVITY_TYPE_UNSUPPORTED"):
        service.create(
            constraint(constraint_id="c-loe", activity_id="LOE-1"),
            auth_context=auth(),
        )
