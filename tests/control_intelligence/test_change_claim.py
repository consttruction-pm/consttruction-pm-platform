import pytest

from construction_pm.control_intelligence.change_claim import ChangeClaimImpact
from construction_pm.control_intelligence.contracts import ControlScope, SourceReference
from construction_pm.control_intelligence.graph import ControlDomain

def test_change_impact_requires_reference_and_evidence() -> None:
    impact = ChangeClaimImpact(
        "link-1", ControlScope("t", "p", 4), "change", "CH-1",
        ControlDomain.SCHEDULE, "activity", "A1", "delay_impact",
        schedule_reference="schedule:A1", evidence_refs=(SourceReference("e1", "document", "/docs/e1", 4),)
    )
    assert impact.requires_application_approval is True

    with pytest.raises(ValueError, match="REFERENCE_REQUIRED"):
        ChangeClaimImpact(
            "link-2", ControlScope("t", "p", 4), "claim", "CL-1",
            ControlDomain.COST, "cost_item", "C1", "cost_impact", evidence_refs=(SourceReference("e1", "document", "/docs/e1", 4),)
        )
