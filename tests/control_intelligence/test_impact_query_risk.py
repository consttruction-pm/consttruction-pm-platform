import pytest

from construction_pm.control_intelligence.contracts import ControlScope, SourceReference
from construction_pm.control_intelligence.graph import ControlDomain
from construction_pm.control_intelligence.impact import ControlImpact, ControlImpactSet, ImpactSeverity, ImpactStatus
from construction_pm.control_intelligence.query import ScheduleQueryAnswer, ScheduleQueryRequest
from construction_pm.control_intelligence.risk import PredictiveScheduleRisk, RiskBand

def scope() -> ControlScope:
    return ControlScope("tenant-1", "project-1", 12)

def source(revision: int = 12) -> SourceReference:
    return SourceReference("s-1", "schedule", "/schedule/A1", revision)

def test_control_impact_is_revision_scoped_and_traceable() -> None:
    impact = ControlImpact(
        "impact-1", scope(), ControlDomain.SCHEDULE, "activity", "A1",
        ControlDomain.COST, "commitment", "C1", "potential_cost_increase",
        ImpactStatus.POTENTIAL, ImpactSeverity.WARNING, "impact.cost.increase", (source(),)
    )
    assert impact.scope.project_revision == 12
    assert impact.source_entity_id == "A1"

def test_control_impact_rejects_stale_evidence_revision() -> None:
    with pytest.raises(ValueError, match="CONTROL_IMPACT_SOURCE_REVISION_MISMATCH"):
        ControlImpact(
            "impact-stale", scope(), ControlDomain.SCHEDULE, "activity", "A1",
            ControlDomain.COST, "commitment", "C1", "potential_cost_increase",
            ImpactStatus.POTENTIAL, ImpactSeverity.WARNING, "impact.cost.increase", (source(11),)
        )

def test_control_impact_set_requires_matching_scope() -> None:
    impact = ControlImpact(
        "impact-1", scope(), ControlDomain.SCHEDULE, "activity", "A1",
        ControlDomain.COST, "commitment", "C1", "potential_cost_increase",
        ImpactStatus.POTENTIAL, ImpactSeverity.WARNING, "impact.cost.increase", (source(),)
    )
    with pytest.raises(ValueError, match="CONTROL_IMPACT_SCOPE_MISMATCH"):
        ControlImpactSet(ControlScope("tenant-1", "project-1", 13), (impact,))

def test_schedule_query_requires_source_backed_answer() -> None:
    request = ScheduleQueryRequest("q-1", scope(), "user-1", "Which activities are at risk?")
    answer = ScheduleQueryAnswer("q-1", scope(), "schedule.query.result", source_refs=(source(),))
    assert request.query_id == answer.query_id
    with pytest.raises(ValueError, match="SOURCE_REQUIRED"):
        ScheduleQueryAnswer("q-2", scope(), "schedule.query.result")

def test_predictive_risk_requires_model_and_sources() -> None:
    risk = PredictiveScheduleRisk(
        "risk-1", scope(), "schedule_delay", "next_reporting_period",
        RiskBand.MEDIUM, RiskBand.HIGH, RiskBand.MEDIUM,
        "risk.title", "risk.detail",
        (ControlDomain.SCHEDULE, ControlDomain.RESOURCE),
        (source(),), "model-v1"
    )
    assert risk.model_version == "model-v1"
    with pytest.raises(ValueError, match="SOURCE_REQUIRED"):
        PredictiveScheduleRisk(
            "risk-2", scope(), "schedule_delay", "next",
            RiskBand.LOW, RiskBand.LOW, RiskBand.LOW,
            "title", "detail", (ControlDomain.SCHEDULE,), (), "model-v1"
        )

def test_predictive_risk_rejects_stale_evidence_revision() -> None:
    with pytest.raises(ValueError, match="PREDICTIVE_RISK_SOURCE_REVISION_MISMATCH"):
        PredictiveScheduleRisk(
            "risk-stale", scope(), "schedule_delay", "next",
            RiskBand.LOW, RiskBand.LOW, RiskBand.LOW,
            "title", "detail", (ControlDomain.SCHEDULE,), (source(11),), "model-v1"
        )

def test_schedule_query_answer_rejects_stale_evidence_revision() -> None:
    stale = SourceReference("s-stale", "schedule", "/schedule/A1", 11)
    with pytest.raises(ValueError, match="SCHEDULE_QUERY_SOURCE_REVISION_MISMATCH"):
        ScheduleQueryAnswer("q-stale", scope(), "schedule.query.result", source_refs=(stale,))
