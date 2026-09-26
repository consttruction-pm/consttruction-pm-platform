from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference, require_enum
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
        if not isinstance(self.risk_id, str) or not self.risk_id.strip() or not isinstance(self.risk_type, str) or not self.risk_type.strip() or not isinstance(self.horizon_key, str) or not self.horizon_key.strip():
            raise ValueError("INVALID_PREDICTIVE_RISK")
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_PREDICTIVE_RISK_SCOPE")
        require_enum(self.likelihood, RiskBand, "INVALID_PREDICTIVE_RISK_LIKELIHOOD")
        require_enum(self.impact, RiskBand, "INVALID_PREDICTIVE_RISK_IMPACT")
        require_enum(self.confidence, RiskBand, "INVALID_PREDICTIVE_RISK_CONFIDENCE")
        if not isinstance(self.title_key, str) or not self.title_key.strip() or not isinstance(self.detail_key, str) or not self.detail_key.strip() or not isinstance(self.model_version, str) or not self.model_version.strip():
            raise ValueError("INVALID_PREDICTIVE_RISK_METADATA")
        if not self.affected_domains:
            raise ValueError("PREDICTIVE_RISK_DOMAIN_REQUIRED")
        for domain in self.affected_domains:
            require_enum(domain, ControlDomain, "INVALID_PREDICTIVE_RISK_DOMAIN")
        if not self.source_refs:
            raise ValueError("PREDICTIVE_RISK_SOURCE_REQUIRED")
