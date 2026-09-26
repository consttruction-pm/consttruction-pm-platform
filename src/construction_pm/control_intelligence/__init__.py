"""Shared control-intelligence contracts and dependency-graph domain primitives.

This package contains domain-level contracts only. It does not perform client-side
or authoritative scheduling, calendar, duration, Progress/EVM, Resource/Cost or
financial calculations.
"""

from .change_claim import ChangeClaimImpact
from .contracts import ControlFinding, ControlIntelligenceResult, ControlScope, FindingSeverity, ProposedAction, SourceReference
from .graph import ControlDomain, DependencyEdge, DependencyGraph, DependencyNode, DependencyRelation
from .impact import ControlImpact, ControlImpactSet, ImpactSeverity, ImpactStatus
from .portfolio import PortfolioControlSnapshot, PortfolioProjectControlInput, build_portfolio_control_snapshot
from .query import ScheduleQueryAnswer, ScheduleQueryKind, ScheduleQueryRequest
from .risk import PredictiveScheduleRisk, RiskBand
from .scenario import ScenarioChange, ScenarioImpact, ScenarioProposal, ScenarioRequest

__all__ = [
    "ChangeClaimImpact",
    "ControlDomain",
    "ControlFinding",
    "ControlImpact",
    "ControlImpactSet",
    "ControlIntelligenceResult",
    "PortfolioControlSnapshot",
    "PortfolioProjectControlInput",
    "build_portfolio_control_snapshot",
    "ControlScope",
    "DependencyEdge",
    "DependencyGraph",
    "DependencyNode",
    "DependencyRelation",
    "FindingSeverity",
    "ImpactSeverity",
    "ImpactStatus",
    "PredictiveScheduleRisk",
    "ProposedAction",
    "RiskBand",
    "ScenarioChange",
    "ScenarioImpact",
    "ScenarioProposal",
    "ScenarioRequest",
    "ScheduleQueryAnswer",
    "ScheduleQueryKind",
    "ScheduleQueryRequest",
    "SourceReference",
]
