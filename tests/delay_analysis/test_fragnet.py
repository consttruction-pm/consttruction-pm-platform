import pytest

from construction_pm.delay_analysis.fragnet import (
    DelayEventFragnet,
    FragnetActivity,
    FragnetRelationship,
    FragnetValidationError,
)
from construction_pm.scheduling.activity import ActivityType
from construction_pm.scheduling.relationships import RelationshipType


def valid_fragnet():
    return DelayEventFragnet(
        event_id="EVT-001",
        title="Late access to work area",
        description="What-if impact of delayed access.",
        activities=(
            FragnetActivity("EVT-001-A", "Access restriction", 3),
            FragnetActivity("EVT-001-B", "Clear access", 0, ActivityType.FINISH_MILESTONE),
        ),
        relationships=(
            FragnetRelationship("A-100", "EVT-001-A", RelationshipType.FS, 0),
            FragnetRelationship("EVT-001-A", "EVT-001-B", RelationshipType.FS, 0),
            FragnetRelationship("EVT-001-B", "A-200", RelationshipType.FS, 0),
        ),
    )


def test_fragnet_accepts_connected_typed_event_network():
    fragnet = valid_fragnet()
    fragnet.validate_against(
        {"A-100", "A-200"},
        {("A-100", "A-200")},
    )
    assert len(fragnet.activities) == 2
    assert len(fragnet.relationships) == 3


def test_fragnet_rejects_activity_id_collision_with_source_schedule():
    with pytest.raises(FragnetValidationError, match="FRAGNET_ACTIVITY_ID_COLLISION"):
        valid_fragnet().validate_against(
            {"A-100", "A-200", "EVT-001-A"},
            set(),
        )


def test_fragnet_rejects_relationship_with_unknown_endpoint():
    fragnet = DelayEventFragnet(
        event_id="EVT-002",
        title="Unknown endpoint",
        description="Invalid link.",
        activities=(FragnetActivity("EVT-002-A", "Event work", 1),),
        relationships=(
            FragnetRelationship("A-100", "EVT-002-A"),
            FragnetRelationship("EVT-002-A", "MISSING-ACTIVITY"),
        ),
    )
    with pytest.raises(FragnetValidationError, match="FRAGNET_RELATIONSHIP_UNKNOWN_ENDPOINT"):
        fragnet.validate_against({"A-100", "A-200"}, set())


def test_fragnet_requires_tie_in_to_existing_schedule():
    with pytest.raises(FragnetValidationError, match="FRAGNET_MUST_TIE_INTO_EXISTING_SCHEDULE"):
        DelayEventFragnet(
            event_id="EVT-003",
            title="Disconnected",
            description="No tie-in.",
            activities=(
                FragnetActivity("EVT-003-A", "Work A", 1),
                FragnetActivity("EVT-003-B", "Work B", 1),
            ),
            relationships=(FragnetRelationship("EVT-003-A", "EVT-003-B"),),
        )


def test_fragnet_rejects_milestone_with_nonzero_duration():
    with pytest.raises(FragnetValidationError, match="FRAGNET_MILESTONE_DURATION_MUST_BE_ZERO"):
        FragnetActivity(
            "EVT-004-M",
            "Finish milestone",
            1,
            ActivityType.FINISH_MILESTONE,
        )


def test_fragnet_rejects_unsupported_activity_semantics():
    with pytest.raises(FragnetValidationError, match="FRAGNET_ACTIVITY_TYPE_NOT_SUPPORTED_BY_SHARED_CORE"):
        FragnetActivity(
            "EVT-005-R",
            "Resource dependent activity",
            2,
            ActivityType.RESOURCE_DEPENDENT,
        )


def test_fragnet_rejects_duplicate_relationship_pair():
    with pytest.raises(FragnetValidationError, match="DUPLICATE_FRAGNET_RELATIONSHIP"):
        DelayEventFragnet(
            event_id="EVT-006",
            title="Duplicate tie-in",
            description="Duplicate links.",
            activities=(FragnetActivity("EVT-006-A", "Work", 1),),
            relationships=(
                FragnetRelationship("A-100", "EVT-006-A"),
                FragnetRelationship("A-100", "EVT-006-A", RelationshipType.SS),
            ),
        )
