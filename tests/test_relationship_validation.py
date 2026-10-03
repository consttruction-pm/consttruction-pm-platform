import pytest

from construction_pm.scheduling.relationships import Relationship, RelationshipType


def test_relationship_requires_string_endpoints():
    with pytest.raises(ValueError):
        Relationship("", "B")
    with pytest.raises(ValueError):
        Relationship("A", " ")
    with pytest.raises(ValueError):
        Relationship(1, "B")


def test_relationship_requires_enum_type():
    with pytest.raises(TypeError):
        Relationship("A", "B", type="FS")


@pytest.mark.parametrize("lag", [True, False])
def test_relationship_rejects_boolean_lag(lag):
    with pytest.raises(TypeError):
        Relationship("A", "B", lag=lag)


def test_relationship_accepts_valid_fields():
    item = Relationship("A", "B", RelationshipType.FS, 2)
    assert item.lag == 2
