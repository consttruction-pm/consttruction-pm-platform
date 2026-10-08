from decimal import Decimal
import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_relationship_api import P6_RELATIONSHIP_API_VERSION, P6RelationshipAPI
from construction_pm.relationship_master_repository import RelationshipMaster, SQLiteRelationshipMasterRepository
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def relationship(scope, *, lag="1.5", revision=0):
    return RelationshipMaster(
        scope=scope,
        relationship_id="rel-1",
        predecessor_id="A-1",
        successor_id="A-2",
        relationship_type=RelationshipType.FS,
        lag_value=Decimal(lag),
        lag_unit=DurationUnit.WORKING_DAY,
        record_revision=revision,
    )


def api(connection):
    return P6RelationshipAPI(SQLiteRelationshipMasterRepository(connection), default_project_policy())


def test_p6_relationship_api_round_trip_preserves_typed_relationship_values():
    service = api(sqlite3.connect(":memory:"))
    scope = BackendScope("t1", "p1", 2)

    created = service.create(relationship(scope), auth_context=auth())
    assert created["contract_version"] == P6_RELATIONSHIP_API_VERSION
    assert created["relationship"]["relationship_type"] == "FS"
    assert created["relationship"]["lag_value"] == "1.5"
    assert created["relationship"]["lag_unit"] == DurationUnit.WORKING_DAY.value
    assert created["relationship"]["record_revision"] == 1

    fetched = service.get(scope, "rel-1", auth_context=auth())
    assert fetched == created
    listed = service.list(scope, auth_context=auth())
    assert listed == (created,)


def test_p6_relationship_api_enforces_scope_and_permissions():
    service = api(sqlite3.connect(":memory:"))
    scope = BackendScope("t1", "p1", 2)
    service.create(relationship(scope), auth_context=auth())

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.get(scope, "rel-1", auth_context=auth(tenant="other"))

    with pytest.raises(AuthorizationError):
        service.create(relationship(scope), auth_context=auth(roles=("viewer",)))


def test_p6_relationship_api_requires_optimistic_revision_for_update():
    service = api(sqlite3.connect(":memory:"))
    scope = BackendScope("t1", "p1", 2)
    service.create(relationship(scope), auth_context=auth())

    updated = relationship(scope, lag="2.25", revision=1)
    result = service.update(updated, expected_revision=1, auth_context=auth())
    assert result["relationship"]["lag_value"] == "2.25"
    assert result["relationship"]["record_revision"] == 2

    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        service.update(relationship(scope, lag="3", revision=2), expected_revision=1, auth_context=auth())
