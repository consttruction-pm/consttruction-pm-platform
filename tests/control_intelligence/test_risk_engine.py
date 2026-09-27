import pytest

from construction_pm.control_intelligence.contracts import ControlScope, SourceReference
from construction_pm.control_intelligence.risk import PredictiveScheduleRisk, RiskBand
from construction_pm.control_intelligence.risk_engine import (
    MODEL_VERSION,
    ScheduleRiskIndicators,
    assess_predictive_schedule_risk,
)


def scope():
    return ControlScope("tenant-1", "project-1", 12)


def source(i: int = 1, revision: int = 12, source_type: str = "schedule"):
    return SourceReference(f"s-{i}", source_type, f"/{source_type}/{i}", revision)


def indicators():
    return ScheduleRiskIndicators(0.9, 0.8, 0.7, 0.6)


def test_predictive_risk_is_deterministic_and_versioned():
    refs = (source(1), source(2), source(3), source(4, source_type="resource"))
    a = assess_predictive_schedule_risk("risk-1", scope(), "next_reporting_period", indicators(), refs)
    b = assess_predictive_schedule_risk("risk-1", scope(), "next_reporting_period", indicators(), refs)
    assert a == b
    assert a.model_version == MODEL_VERSION
    assert a.attributes["risk_score"] == 0.785
    assert a.likelihood is RiskBand.HIGH
    assert a.confidence is RiskBand.HIGH


def test_cross_domain_sources_must_share_the_authoritative_revision():
    refs = (source(1, source_type="schedule"), source(2, source_type="resource"))
    result = assess_predictive_schedule_risk("risk-1", scope(), "next", indicators(), refs)
    assert {ref.source_type for ref in result.source_refs} == {"schedule", "resource"}
    assert {ref.revision for ref in result.source_refs} == {12}


def test_stale_revision_source_is_rejected():
    with pytest.raises(ValueError, match="STALE_PREDICTIVE_RISK_SOURCE"):
        assess_predictive_schedule_risk(
            "risk-1",
            scope(),
            "next",
            indicators(),
            (source(1), source(2, 11, "resource")),
        )


def test_missing_sources_are_rejected():
    with pytest.raises(ValueError, match="SOURCE_REQUIRED"):
        assess_predictive_schedule_risk("risk-1", scope(), "next", indicators(), ())


def test_indicator_range_is_rejected():
    with pytest.raises(ValueError, match="INVALID_SCHEDULE_RISK_INDICATORS"):
        ScheduleRiskIndicators(1.1, 0.0, 0.0, 0.0)


def test_invalid_confidence_is_rejected_by_predictive_risk_contract():
    with pytest.raises(ValueError, match="INVALID_PREDICTIVE_RISK_CONFIDENCE"):
        PredictiveScheduleRisk(
            risk_id="risk-1",
            scope=scope(),
            risk_type="schedule_delay",
            horizon_key="next",
            likelihood=RiskBand.HIGH,
            impact=RiskBand.HIGH,
            confidence="high",
            title_key="predictive.schedule_risk.title",
            detail_key="predictive.schedule_risk.detail",
            affected_domains=(),
            source_refs=(source(),),
            model_version=MODEL_VERSION,
        )
