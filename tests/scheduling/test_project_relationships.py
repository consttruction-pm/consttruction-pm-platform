import pytest

from construction_pm.scheduling.project_relationships import (
    ExternalProjectRelationshipError,
    resolve_project_relationships,
)
from construction_pm.scheduling.relationships import Relationship


def test_ignore_other_project_relationships_keeps_only_internal_edges():
    internal = Relationship("A", "B")
    external = Relationship("B", "C")
    result = resolve_project_relationships(
        (internal, external),
        activity_project_ids={"A": "P1", "B": "P1", "C": "P2"},
        scheduled_project_id="P1",
        ignore_other_project_relationships=True,
    )
    assert result == (internal,)


def test_external_relationship_is_preserved_when_ignore_is_disabled():
    external = Relationship("B", "C")
    result = resolve_project_relationships(
        (external,),
        activity_project_ids={"B": "P1", "C": "P2"},
        scheduled_project_id="P1",
        ignore_other_project_relationships=False,
    )
    assert result == (external,)


def test_unrelated_project_relationship_is_not_injected_into_current_schedule():
    unrelated = Relationship("C", "D")
    result = resolve_project_relationships(
        (unrelated,),
        activity_project_ids={"C": "P2", "D": "P3"},
        scheduled_project_id="P1",
        ignore_other_project_relationships=False,
    )
    assert result == ()


def test_missing_project_membership_is_rejected_instead_of_guessed():
    with pytest.raises(
        ExternalProjectRelationshipError,
        match="MISSING_PROJECT_ID_FOR_RELATIONSHIP_ENDPOINT",
    ):
        resolve_project_relationships(
            (Relationship("A", "B"),),
            activity_project_ids={"A": "P1"},
            scheduled_project_id="P1",
            ignore_other_project_relationships=False,
        )
