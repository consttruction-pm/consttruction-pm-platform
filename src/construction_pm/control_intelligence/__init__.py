"""Shared control-intelligence contracts and dependency-graph domain primitives.

This package contains domain-level contracts only. It does not perform client-side
or authoritative scheduling, calendar, duration, Progress/EVM, Resource/Cost or
financial calculations.
"""

from .contracts import ControlFinding, ControlIntelligenceResult, ControlScope, ProposedAction, SourceReference
from .graph import DependencyEdge, DependencyGraph, DependencyNode
from .scenario import ScenarioChange, ScenarioImpact, ScenarioProposal, ScenarioRequest

__all__ = [
    "ControlFinding", "ControlIntelligenceResult", "ControlScope",
    "DependencyEdge", "DependencyGraph", "DependencyNode",
    "ProposedAction", "ScenarioChange", "ScenarioImpact",
    "ScenarioProposal", "ScenarioRequest", "SourceReference",
]
