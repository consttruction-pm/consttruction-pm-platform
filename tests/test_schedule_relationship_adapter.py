from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.relationship_master_repository import RelationshipMaster
from construction_pm.schedule_relationship_adapter import (
    RelationshipMasterScheduleAdapterError,
    relationship_master_to_date_relationship,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


def _relationship(**changes):
    values = {
        "scope": BackendScope("T-1", "P-1", 3),
        "relationship_id": "REL-1",
        "predecessor_id": "A-1",
        "successor_id": "A-2",
        "relationship_type": RelationshipType.FS,
        "lag_value": Decimal("0"),
        "lag_unit": DurationUnit.WORKING_DAY,
    }
    values.update(changes)
    return RelationshipMaster(**values)


def test_adapter_preserves_relationship_endpoints_type_and_whole_day_lag():
    source = _relationship(
        relationship_type=RelationshipType.SS,
        lag_value=Decimal("-2"),
    )

    result = relationship_master_to_date_relationship(source)

    assert result.predecessor_id == "A-1"
    assert result.successor_id == "A-2"
    assert result.type is RelationshipType.SS
    assert result.lag == -2


def test_adapter_rejects_working_hour_lag_without_calendar_conversion():
    source = _relationship(
        lag_value=Decimal("8"),
        lag_unit=DurationUnit.WORKING_HOUR,
    )

    with pytest.raises(RelationshipMasterScheduleAdapterError, match="UNSUPPORTED_LAG_UNIT"):
        relationship_master_to_date_relationship(source)


def test_adapter_rejects_fractional_working_day_lag_without_rounding():
    source = _relationship(lag_value=Decimal("1.5"))

    with pytest.raises(
        RelationshipMasterScheduleAdapterError,
        match="FRACTIONAL_WORKING_DAY_LAG_NOT_SUPPORTED",
    ):
        relationship_master_to_date_relationship(source)


@pytest.mark.parametrize(
    ("predecessor_id", "successor_id"),
    [("A-1", "A-1"), ("", "A-2"), ("A-1", "")],
)
def test_adapter_rejects_invalid_relationship_endpoints(predecessor_id, successor_id):
    source = _relationship(
        predecessor_id=predecessor_id,
        successor_id=successor_id,
    )

    with pytest.raises(RelationshipMasterScheduleAdapterError, match="INVALID_RELATIONSHIP_MASTER"):
        relationship_master_to_date_relationship(source)
