from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference
from .graph import ControlDomain

class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass(frozen=True)
class PredictiveScheduleRisk:
    risk_id: str
    scope: ControlScope
    risk_type: str
    horizon_key: str
    likelihood: RiskBand
    impact: RiskBand
    confidence: RiskBand
    title_key: str
    detail_key: str
    affected_domains: Tuple[ControlDomain, ...]
    source_refs: Tuple[SourceReference, ...]
    model_version: str
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.risk_id or not self.risk_type or not self.horizon_key:
            raise ValueError("INVALID_PREDICTIVE_RISK")
        if not self.title_key or not self.detail_key or not self.model_version:
            raise ValueError("INVALID_PREDICTIVE_RISK_METADATA")
        if not self.affected_domains:
            raise ValueError("PREDICTIVE_RISK_DOMAIN_REQUIRED")
        if not self.source_refs:
            raise ValueError("PREDICTIVE_RISK_SOURCE_REQUIRED")
