import pytest
from decimal import Decimal

from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit, LagQuantity, TimeQuantity
from construction_pm.scheduling.time_forward_pass import TimeActivity, TimeRelationship


def _duration():
    return TimeQuantity(Decimal("1"), DurationUnit.WORKING_HOUR)


@pytest.mark.parametrize("value", [1, True, None])
def test_time_activity_requires_string_id(value):
    with pytest.raises(ValueError):
        TimeActivity(value, _duration())


@pytest.mark.parametrize("pred", [1, True, None])
def test_time_relationship_requires_string_predecessor(pred):
    with pytest.raises(ValueError):
        TimeRelationship(pred, "B")


def test_time_relationship_requires_enum_type():
    with pytest.raises(TypeError):
        TimeRelationship("A", "B", type="FS")


def test_valid_time_models():
    activity = TimeActivity("A", _duration())
    relationship = TimeRelationship("A", "B", RelationshipType.FS, LagQuantity.working_hours(0))
    assert activity.id == "A"
    assert relationship.type is RelationshipType.FS
