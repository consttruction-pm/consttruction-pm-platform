import pytest

from construction_pm.control_intelligence.contracts import ControlScope, SourceReference
from construction_pm.control_intelligence.risk import RiskBand
from construction_pm.control_intelligence.risk_engine import (
    MODEL_VERSION,
    ScheduleRiskIndicators,
    assess_predictive_schedule_risk,
)


def scope():
    return ControlScope("tenant-1", "project-1", 12)


def source(i: int = 1, revision: int = 12):
    return SourceReference(f"s-{i}", "schedule", f"/schedule/{i}", revision)


def indicators():
    return ScheduleRiskIndicators(0.9, 0.8, 0.7, 0.6)


def test_predictive_risk_is_deterministic_and_versioned():
    a = assess_predictive_schedule_risk("risk-1", scope(), "next_reporting_period", indicators(), (source(1), source(2), source(3), source(4)))
    b = assess_predictive_schedule_risk("risk-1", scope(), "next_reporting_period", indicators(), (source(1), source(2), source(3), source(4)))
    assert a == b
    assert a.model_version == MODEL_VERSION
    assert a.attributes["risk_score"] == 0.81
    assert a.likelihood is RiskBand.CRITICAL


def test_stale_revision_source_is_rejected():
    with pytest.raises(ValueError, match="STALE_PREDICTIVE_RISK_SOURCE"):
        assess_predictive_schedule_risk("risk-1", scope(), "next", indicators(), (source(1, 11),))


def test_missing_sources_are_rejected():
    with pytest.raises(ValueError, match="SOURCE_REQUIRED"):
        assess_predictive_schedule_risk("risk-1", scope(), "next", indicators(), ())


def test_indicator_range_is_rejected():
    with pytest.raises(ValueError, match="INVALID_SCHEDULE_RISK_INDICATORS"):
        ScheduleRiskIndicators(1.1, 0.0, 0.0, 0.0)
