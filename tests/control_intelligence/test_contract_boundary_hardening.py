from datetime import datetime, tzinfo
from dataclasses import replace

import pytest

from construction_pm.control_intelligence.change_claim import ChangeClaimImpact
from construction_pm.control_intelligence.contracts import (
    ControlFinding,
    ControlIntelligenceResult,
    ControlScope,
    FindingSeverity,
    ProposedAction,
    SourceReference,
)
from construction_pm.control_intelligence.graph import ControlDomain
from construction_pm.control_intelligence.impact import ControlImpact, ImpactSeverity, ImpactStatus
from construction_pm.control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from construction_pm.control_intelligence.risk import PredictiveScheduleRisk, RiskBand
from construction_pm.control_intelligence.scenario import ScenarioChange, ScenarioImpact, ScenarioProposal


def scope() -> ControlScope:
    return ControlScope("tenant-1", "project-1", 12)


def source() -> SourceReference:
    return SourceReference("s-1", "document", "/source/s-1", 12)


class NoOffsetTZ(tzinfo):
    def utcoffset(self, dt):
        return None


def test_control_scope_rejects_non_string_identity() -> None:
    with pytest.raises(ValueError, match="INVALID_CONTROL_SCOPE"):
        ControlScope(123, "project-1", 1)  # type: ignore[arg-type]


def test_control_finding_rejects_string_enums() -> None:
    with pytest.raises(ValueError, match="INVALID_CONTROL_FINDING_DOMAIN"):
        ControlFinding("f-1", "cost", FindingSeverity.WARNING, "title", "detail", (source(),))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="INVALID_CONTROL_FINDING_SEVERITY"):
        ControlFinding("f-1", ControlDomain.COST, "warning", "title", "detail", (source(),))  # type: ignore[arg-type]


def test_control_result_rejects_timezone_without_utc_offset() -> None:
    with pytest.raises(ValueError, match="TIMEZONE_AWARE"):
        ControlIntelligenceResult(
            "result-1",
            scope(),
            datetime(2026, 1, 1, tzinfo=NoOffsetTZ()),
            "result.summary",
            source_refs=(source(),),
        )


def test_proposed_action_rejects_non_boolean_approval_flag() -> None:
    with pytest.raises(ValueError, match="INVALID_PROPOSED_ACTION_APPROVAL_FLAG"):
        ProposedAction("a-1", "refresh", "action.refresh", source_refs=(source(),), requires_approval="yes")  # type: ignore[arg-type]


def test_impact_rejects_string_enums() -> None:
    with pytest.raises(ValueError, match="INVALID_CONTROL_IMPACT_SOURCE_DOMAIN"):
        ControlImpact(
            "impact-1", scope(), "schedule", "activity", "A1",
            ControlDomain.COST, "commitment", "C1", "cost_increase",
            ImpactStatus.POTENTIAL, ImpactSeverity.WARNING, "detail", (source(),)
        )
    with pytest.raises(ValueError, match="INVALID_CONTROL_IMPACT_STATUS"):
        ControlImpact(
            "impact-1", scope(), ControlDomain.SCHEDULE, "activity", "A1",
            ControlDomain.COST, "commitment", "C1", "cost_increase",
            "potential", ImpactSeverity.WARNING, "detail", (source(),)
        )


def test_query_rejects_string_kind() -> None:
    with pytest.raises(ValueError, match="INVALID_SCHEDULE_QUERY_KIND"):
        ScheduleQueryRequest(
            "q-1", scope(), "user-1", "What is delayed?",
            kind="fact",  # type: ignore[arg-type]
        )


def test_risk_rejects_string_bands_and_domains() -> None:
    with pytest.raises(ValueError, match="INVALID_PREDICTIVE_RISK_LIKELIHOOD"):
        PredictiveScheduleRisk(
            "r-1", scope(), "delay", "next", "medium", RiskBand.HIGH, RiskBand.MEDIUM,
            "title", "detail", (ControlDomain.SCHEDULE,), (source(),), "model-v1"
        )
    with pytest.raises(ValueError, match="INVALID_PREDICTIVE_RISK_DOMAIN"):
        PredictiveScheduleRisk(
            "r-1", scope(), "delay", "next", RiskBand.MEDIUM, RiskBand.HIGH, RiskBand.MEDIUM,
            "title", "detail", ("schedule",), (source(),), "model-v1"  # type: ignore[arg-type]
        )


def test_scenario_rejects_string_domain_and_mutation_flag_type() -> None:
    with pytest.raises(ValueError, match="INVALID_SCENARIO_CHANGE_DOMAIN"):
        ScenarioChange("c-1", "schedule", "activity", "A1", "set_start", {"value": "2030-01-01"}, (source(),))  # type: ignore[arg-type]

    change = ScenarioChange("c-1", ControlDomain.SCHEDULE, "activity", "A1", "set_start", {"value": "2030-01-01"}, (source(),))
    impact = ScenarioImpact(ControlDomain.COST, "commitment", "C1", "potential_increase", "impact.cost", (source(),))
    with pytest.raises(ValueError, match="INVALID_SCENARIO_MUTATION_FLAG"):
        ScenarioProposal("scenario-1", scope(), (impact,), (change,), authoritative_mutation_allowed="false")  # type: ignore[arg-type]


def test_change_claim_rejects_string_domain_and_non_boolean_approval() -> None:
    with pytest.raises(ValueError, match="INVALID_CHANGE_CLAIM_DOMAIN"):
        ChangeClaimImpact(
            "link-1", scope(), "change", "CH-1", "schedule", "activity", "A1", "delay",
            schedule_reference="schedule:A1", evidence_refs=(source(),)
        )  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="INVALID_CHANGE_CLAIM_APPROVAL_FLAG"):
        ChangeClaimImpact(
            "link-1", scope(), "change", "CH-1", ControlDomain.SCHEDULE, "activity", "A1", "delay",
            schedule_reference="schedule:A1", evidence_refs=(source(),), requires_application_approval=1
        )  # type: ignore[arg-type]
