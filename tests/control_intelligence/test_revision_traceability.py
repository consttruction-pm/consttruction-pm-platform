from datetime import datetime, timezone

import pytest

from construction_pm.control_intelligence.contracts import (
    ControlFinding,
    ControlIntelligenceResult,
    ControlScope,
    FindingSeverity,
    ProposedAction,
    SourceReference,
)
from construction_pm.control_intelligence.graph import ControlDomain
from construction_pm.control_intelligence.impact import ControlImpactSet
from construction_pm.control_intelligence.query import ScheduleQueryAnswer
from construction_pm.control_intelligence.risk import PredictiveScheduleRisk, RiskBand


def source(source_id: str = "s-1") -> SourceReference:
    return SourceReference(source_id, "document", f"/source/{source_id}", 12)


def scope() -> ControlScope:
    return ControlScope("tenant-1", "project-1", 12)


def test_result_and_answer_remain_bound_to_same_project_revision() -> None:
    result = ControlIntelligenceResult(
        "result-1",
        scope(),
        datetime.now(timezone.utc),
        "control.summary",
        source_refs=(source(),),
    )
    answer = ScheduleQueryAnswer(
        "query-1",
        scope(),
        "schedule.query.result",
        source_refs=(source("query-source"),),
    )

    assert result.scope == answer.scope
    assert result.scope.project_revision == 12


def test_proposed_action_defaults_to_human_approval() -> None:
    action = ProposedAction(
        "action-1",
        "refresh_baseline",
        "action.refresh_baseline",
        source_refs=(source(),),
    )
    assert action.requires_approval is True


def test_impact_set_requires_at_least_one_traceable_impact() -> None:
    with pytest.raises(ValueError, match="CONTROL_IMPACTS_REQUIRED"):
        ControlImpactSet(scope(), ())


def test_predictive_risk_requires_cross_domain_impact_context() -> None:
    risk = PredictiveScheduleRisk(
        "risk-1",
        scope(),
        "schedule_delay",
        "next_reporting_period",
        RiskBand.MEDIUM,
        RiskBand.HIGH,
        RiskBand.HIGH,
        "risk.title",
        "risk.detail",
        (ControlDomain.SCHEDULE, ControlDomain.COST),
        (source(),),
        "model-v1",
    )
    assert set(risk.affected_domains) == {
        ControlDomain.SCHEDULE,
        ControlDomain.COST,
    }


def test_finding_requires_source_evidence() -> None:
    with pytest.raises(ValueError, match="SOURCE_REQUIRED"):
        ControlFinding(
            "finding-1",
            ControlDomain.SCHEDULE,
            FindingSeverity.WARNING,
            "finding.title",
            "finding.detail",
        )


def test_revision_values_match_shared_safe_integer_boundary() -> None:
    with pytest.raises(ValueError, match="INVALID_PROJECT_REVISION"):
        ControlScope("tenant-1", "project-1", 9_007_199_254_740_992)
    with pytest.raises(ValueError, match="INVALID_PROJECT_REVISION"):
        ControlScope("tenant-1", "project-1", True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="INVALID_SOURCE_REVISION"):
        SourceReference("s-1", "document", "/source/s-1", 9_007_199_254_740_992)
    with pytest.raises(ValueError, match="INVALID_SOURCE_REVISION"):
        SourceReference("s-1", "document", "/source/s-1", True)  # type: ignore[arg-type]


def test_dependency_revisions_match_shared_safe_integer_boundary() -> None:
    from construction_pm.control_intelligence.graph import DependencyEdge, DependencyNode, DependencyRelation

    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_NODE_REVISION"):
        DependencyNode("n-1", ControlDomain.SCHEDULE, "activity", "A-1", 9_007_199_254_740_992)
    with pytest.raises(ValueError, match="INVALID_SOURCE_REVISION"):
        DependencyEdge("n-1", "n-2", DependencyRelation.IMPACTS, 9_007_199_254_740_992, 1)
