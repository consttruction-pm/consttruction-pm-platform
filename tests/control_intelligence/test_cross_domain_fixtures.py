from datetime import datetime, timezone

import pytest

from construction_pm.control_intelligence.contracts import (
    ControlScope,
    ControlFinding,
    ControlIntelligenceResult,
    FindingSeverity,
    SourceReference,
)
from construction_pm.control_intelligence.graph import (
    ControlDomain,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyRelation,
)
from construction_pm.control_intelligence.impact import (
    ControlImpact,
    ControlImpactSet,
    ImpactSeverity,
    ImpactStatus,
)
from construction_pm.control_intelligence.scenario import (
    ScenarioChange,
    ScenarioProposal,
    ScenarioRequest,
)


def _scope(revision: int = 7) -> ControlScope:
    return ControlScope("tenant-1", "project-1", revision)


def _source(revision: int = 7) -> SourceReference:
    return SourceReference(
        source_id="src-001",
        source_type="schedule_snapshot",
        locator="schedule/activity/A-100",
        revision=revision,
        content_hash="sha256:fixture",
    )


def test_cross_domain_fixture_covers_control_chain() -> None:
    graph = DependencyGraph(scope=_scope())

    nodes = [
        DependencyNode("schedule:A-100", ControlDomain.SCHEDULE, "activity", "A-100", 7),
        DependencyNode("progress:A-100", ControlDomain.PROGRESS, "activity_progress", "A-100", 7),
        DependencyNode("evm:A-100", ControlDomain.EVM, "earned_value", "A-100", 7),
        DependencyNode("resource:R-10", ControlDomain.RESOURCE, "resource_assignment", "R-10", 7),
        DependencyNode("cost:C-10", ControlDomain.COST, "cost_item", "C-10", 7),
        DependencyNode("change:CH-10", ControlDomain.CHANGE, "change_order", "CH-10", 7),
        DependencyNode("claim:CL-10", ControlDomain.CLAIM, "claim", "CL-10", 7),
    ]
    for item in nodes:
        graph.add_node(item)

    relations = [
        ("schedule:A-100", "progress:A-100", DependencyRelation.DERIVED_FROM),
        ("progress:A-100", "evm:A-100", DependencyRelation.DERIVED_FROM),
        ("resource:R-10", "schedule:A-100", DependencyRelation.ALLOCATES),
        ("cost:C-10", "resource:R-10", DependencyRelation.IMPACTS),
        ("change:CH-10", "schedule:A-100", DependencyRelation.IMPACTS),
        ("claim:CL-10", "change:CH-10", DependencyRelation.CLAIMS_AGAINST),
    ]
    for source, target, relation in relations:
        graph.add_edge(DependencyEdge(source, target, relation, 7, 7))

    graph.validate()

    assert len(graph.nodes) == 7
    assert len(graph.edges) == len(relations)
    assert {edge.relation for edge in graph.edges} == {relation for _, _, relation in relations}


def test_impact_fixture_preserves_scope_and_traceability() -> None:
    source = _source()
    impact = ControlImpact(
        impact_id="impact-001",
        scope=_scope(),
        source_domain=ControlDomain.CHANGE,
        source_entity_type="change_order",
        source_entity_id="CH-10",
        target_domain=ControlDomain.SCHEDULE,
        target_entity_type="activity",
        target_entity_id="A-100",
        impact_type="schedule_delay",
        status=ImpactStatus.POTENTIAL,
        severity=ImpactSeverity.WARNING,
        detail_key="control.schedule.delay",
        source_refs=(source,),
    )
    result = ControlImpactSet(scope=_scope(), impacts=(impact,))

    assert result.scope == _scope()
    assert result.impacts[0].source_refs == (source,)


def test_control_result_requires_authoritative_source_reference() -> None:
    source = _source()
    finding = ControlFinding(
        finding_id="finding-001",
        domain=ControlDomain.SCHEDULE,
        severity=FindingSeverity.WARNING,
        title_key="finding.title",
        detail_key="finding.detail",
        source_refs=(source,),
    )
    result = ControlIntelligenceResult(
        result_id="result-001",
        scope=_scope(),
        generated_at=datetime.now(timezone.utc),
        summary_key="control.summary",
        findings=(finding,),
        source_refs=(source,),
    )

    assert result.scope == _scope()
    assert result.findings == (finding,)
    assert result.source_refs == (source,)


def test_scenario_fixture_is_explicitly_non_mutating() -> None:
    source = _source()
    change = ScenarioChange(
        change_id="scenario-change-001",
        domain=ControlDomain.SCHEDULE,
        entity_type="activity",
        entity_id="A-100",
        operation="propose_shift",
        proposed_value={"delta_days": 2},
        source_refs=(source,),
    )
    request = ScenarioRequest(
        scenario_id="scenario-001",
        scope=_scope(),
        requested_by="user-1",
        purpose_key="scenario.test",
        changes=(change,),
        source_refs=(source,),
    )
    proposal = ScenarioProposal(
        scenario_id=request.scenario_id,
        base_scope=request.scope,
        impacts=(),
        proposed_changes=request.changes,
    )

    assert proposal.authoritative_mutation_allowed is False
    with pytest.raises(ValueError, match="SCENARIO_CANNOT_MUTATE_AUTHORITATIVE_STATE"):
        ScenarioProposal(
            scenario_id="scenario-002",
            base_scope=_scope(),
            impacts=(),
            proposed_changes=(change,),
            authoritative_mutation_allowed=True,
        )
