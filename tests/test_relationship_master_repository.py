from decimal import Decimal
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    RelationshipPersistenceError,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("T-1", "P-1", revision)


def relationship(
    relationship_id: str = "R-1",
    relationship_type: RelationshipType = RelationshipType.FS,
    lag: str = "0",
    unit: DurationUnit = DurationUnit.WORKING_DAY,
    revision: int = 7,
) -> RelationshipMaster:
    return RelationshipMaster(
        scope(revision),
        relationship_id,
        "A-1",
        "A-2",
        relationship_type,
        Decimal(lag),
        unit,
    )


@pytest.mark.parametrize("relationship_type", list(RelationshipType))
def test_relationship_master_round_trip_supports_all_relationship_types(relationship_type):
    repo = SQLiteRelationshipMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(relationship(relationship_type=relationship_type))
    assert stored.relationship_type is relationship_type
    assert repo.get(scope(), "R-1") == stored


def test_relationship_master_preserves_signed_lag_and_unit():
    repo = SQLiteRelationshipMasterRepository(sqlite3.connect(":memory:"))
    stored = repo.save(
        relationship(lag="-2.5", unit=DurationUnit.WORKING_HOUR)
    )
    assert stored.lag_value == Decimal("-2.5")
    assert stored.lag_unit is DurationUnit.WORKING_HOUR
    assert stored.lag.value == Decimal("-2.5")
    assert stored.lag.unit is DurationUnit.WORKING_HOUR


def test_relationship_master_rejects_self_relationship():
    with pytest.raises(RelationshipPersistenceError, match="SELF_RELATIONSHIP"):
        relationship().validate()


def test_relationship_master_rejects_stale_update():
    repo = SQLiteRelationshipMasterRepository(sqlite3.connect(":memory:"))
    repo.save(relationship())
    with pytest.raises(RelationshipPersistenceError, match="REVISION_CONFLICT"):
        repo.save(relationship(lag="1"), expected_revision=0)


def test_relationship_master_rejects_cross_revision_read():
    repo = SQLiteRelationshipMasterRepository(sqlite3.connect(":memory:"))
    repo.save(relationship())
    with pytest.raises(RelationshipPersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "R-1")


def test_relationship_master_lists_deterministically():
    repo = SQLiteRelationshipMasterRepository(sqlite3.connect(":memory:"))
    repo.save(relationship("R-2"))
    repo.save(relationship("R-1"))
    assert tuple(r.relationship_id for r in repo.list(scope())) == ("R-1", "R-2")
