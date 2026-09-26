import pytest

from construction_pm.control_intelligence.contracts import ControlScope, SourceReference
from construction_pm.control_intelligence.graph import ControlDomain
from construction_pm.control_intelligence.scenario import ScenarioChange, ScenarioImpact, ScenarioProposal, ScenarioRequest

def source(source_id: str = "schedule-1") -> SourceReference:
    return SourceReference(source_id, "schedule", "/schedule/" + source_id, 7)

def change() -> ScenarioChange:
    return ScenarioChange("change-1", ControlDomain.SCHEDULE, "activity", "A1", "set_start", {"value": "2030-01-01"}, (source(),))

def test_scenario_request_is_revision_scoped_and_traceable() -> None:
    request = ScenarioRequest("scenario-1", ControlScope("tenant-1", "project-1", 7), "user-1", "scenario.delay_activity", (change(),), source_refs=(source(),))
    assert request.scope.project_revision == 7
    assert request.changes[0].entity_id == "A1"

def test_scenario_proposal_cannot_be_authoritative() -> None:
    proposal = ScenarioProposal("scenario-1", ControlScope("tenant-1", "project-1", 7), impacts=(ScenarioImpact(ControlDomain.COST, "commitment", "C1", "potential_increase", "impact.cost.increase", (source("cost-1"),)),), proposed_changes=(change(),))
    assert proposal.authoritative_mutation_allowed is False
    with pytest.raises(ValueError, match="SCENARIO_CANNOT_MUTATE"):
        ScenarioProposal("scenario-1", ControlScope("tenant-1", "project-1", 7), impacts=proposal.impacts, proposed_changes=proposal.proposed_changes, authoritative_mutation_allowed=True)
