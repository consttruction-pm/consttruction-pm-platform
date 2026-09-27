"""Deterministic predictive schedule-risk baseline over authoritative control indicators.

This module deliberately does not calculate CPM/P6 scheduling semantics. It consumes
already-computed project-control indicators and produces an auditable risk assessment.
"""
from dataclasses import dataclass
from typing import Tuple

from .contracts import ControlScope, SourceReference
from .risk import PredictiveScheduleRisk, RiskBand
from .graph import ControlDomain

MODEL_VERSION = "schedule-risk-baseline-v1"


@dataclass(frozen=True)
class ScheduleRiskIndicators:
    """Normalized authoritative indicators; each value must be in [0, 1]."""
    schedule_variance_ratio: float
    critical_float_pressure: float
    overdue_activity_ratio: float
    resource_variance_ratio: float

    def __post_init__(self) -> None:
        values = (self.schedule_variance_ratio, self.critical_float_pressure,
                  self.overdue_activity_ratio, self.resource_variance_ratio)
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in values):
            raise ValueError("INVALID_SCHEDULE_RISK_INDICATORS")

    def score(self) -> float:
        # Fixed, versioned weights. Inputs are indicators, not replacement schedule calculations.
        return round(
            self.schedule_variance_ratio * 0.35
            + self.critical_float_pressure * 0.30
            + self.overdue_activity_ratio * 0.20
            + self.resource_variance_ratio * 0.15,
            6,
        )


def _band(score: float) -> RiskBand:
    if score >= 0.80:
        return RiskBand.CRITICAL
    if score >= 0.60:
        return RiskBand.HIGH
    if score >= 0.30:
        return RiskBand.MEDIUM
    return RiskBand.LOW


def _confidence(indicators: ScheduleRiskIndicators, source_refs: Tuple[SourceReference, ...]) -> RiskBand:
    # Confidence expresses evidence completeness for this deterministic baseline, not model accuracy.
    count = len(source_refs)
    observed = sum(v > 0 for v in (
        indicators.schedule_variance_ratio,
        indicators.critical_float_pressure,
        indicators.overdue_activity_ratio,
        indicators.resource_variance_ratio,
    ))
    if count >= 4 and observed >= 3:
        return RiskBand.HIGH
    if count >= 2 and observed >= 1:
        return RiskBand.MEDIUM
    return RiskBand.LOW


def assess_predictive_schedule_risk(
    risk_id: str,
    scope: ControlScope,
    horizon_key: str,
    indicators: ScheduleRiskIndicators,
    source_refs: Tuple[SourceReference, ...],
) -> PredictiveScheduleRisk:
    """Produce a revision-safe, deterministic predictive-risk result."""
    if not source_refs:
        raise ValueError("PREDICTIVE_RISK_SOURCE_REQUIRED")
    if any(ref.revision != scope.project_revision for ref in source_refs):
        raise ValueError("STALE_PREDICTIVE_RISK_SOURCE")
    score = indicators.score()
    band = _band(score)
    return PredictiveScheduleRisk(
        risk_id=risk_id,
        scope=scope,
        risk_type="schedule_delay",
        horizon_key=horizon_key,
        likelihood=band,
        impact=band,
        confidence=_confidence(indicators, source_refs),
        title_key="predictive.schedule_risk.title",
        detail_key="predictive.schedule_risk.detail",
        affected_domains=(ControlDomain.SCHEDULE, ControlDomain.RESOURCE),
        source_refs=source_refs,
        model_version=MODEL_VERSION,
        attributes={"risk_score": score, "model_type": "deterministic_baseline"},
    )
