from datetime import datetime, timezone

import pytest

from construction_pm.control_intelligence.contracts import (
    ControlFinding,
    ControlIntelligenceResult,
    ControlScope,
    FindingSeverity,
    SourceReference,
)
from construction_pm.control_intelligence.graph import ControlDomain
from construction_pm.control_intelligence.scenario import ScenarioImpact, ScenarioProposal
from construction_pm.control_intelligence_api import (
    ControlIntelligenceResultEnvelope,
    ScenarioProposalEnvelope,
    ensure_read_only_scenario,
)


def ref():
    return SourceReference("src-1", "schedule", "activity/1", 7)


def result():
    return ControlIntelligenceResult(
        result_id="result-1",
        scope=ControlScope("T-1", "P-1", 7),
        generated_at=datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc),
        summary_key="control.summary",
        findings=(
            ControlFinding(
                "finding-1",
                ControlDomain.SCHEDULE,
                FindingSeverity.WARNING,
                "finding.title",
                "finding.detail",
                (ref(),),
            ),
        ),
        source_refs=(ref(),),
    )


def test_result_envelope_is_versioned_and_preserves_audit_provenance():
    payload = ControlIntelligenceResultEnvelope("control-intelligence.v1", result()).to_dict()

    assert payload["contract_version"] == "control-intelligence.v1"
    assert payload["tenant_id"] == "T-1"
    assert payload["project_id"] == "P-1"
    assert payload["project_revision"] == 7
    assert payload["generated_at"].endswith("+00:00")
    assert payload["source_refs"] == ("src-1",)
    assert payload["findings"][0]["source_refs"] == ("src-1",)


def test_scenario_envelope_explicitly_remains_non_authoritative():
    proposal = ScenarioProposal(
        scenario_id="scenario-1",
        base_scope=ControlScope("T-1", "P-1", 7),
        impacts=(
            ScenarioImpact(
                ControlDomain.SCHEDULE,
                "activity",
                "A-1",
                "delay",
                "scenario.delay",
                (ref(),),
            ),
        ),
        proposed_changes=(),
    )

    payload = ScenarioProposalEnvelope("control-intelligence.scenario.v1", proposal).to_dict()

    assert payload["authoritative_mutation_allowed"] is False
    assert ensure_read_only_scenario(proposal) is proposal


def test_authoritative_scenario_mutation_is_rejected():
    with pytest.raises(ValueError, match="SCENARIO_CANNOT_MUTATE_AUTHORITATIVE_STATE"):
        object.__setattr__(
            ScenarioProposal(
                scenario_id="scenario-1",
                base_scope=ControlScope("T-1", "P-1", 7),
                impacts=(),
                proposed_changes=(),
            ),
            "authoritative_mutation_allowed",
            True,
        )
