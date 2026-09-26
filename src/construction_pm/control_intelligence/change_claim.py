from dataclasses import dataclass, field
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference, require_enum
from .graph import ControlDomain


@dataclass(frozen=True)
class ChangeClaimImpact:
    link_id: str
    scope: ControlScope
    record_type: str
    record_id: str
    impacted_domain: ControlDomain
    impacted_entity_type: str
    impacted_entity_id: str
    impact_type: str
    schedule_reference: str | None = None
    cost_reference: str | None = None
    evidence_refs: Tuple[SourceReference, ...] = ()
    requires_application_approval: bool = True
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.link_id, str) or not self.link_id.strip() or not isinstance(self.record_id, str) or not self.record_id.strip() or not isinstance(self.impact_type, str) or not self.impact_type.strip():
            raise ValueError("INVALID_CHANGE_CLAIM_IMPACT")
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_CHANGE_CLAIM_SCOPE")
        if self.record_type not in {"change", "claim"}:
            raise ValueError("INVALID_CHANGE_CLAIM_RECORD_TYPE")
        require_enum(self.impacted_domain, ControlDomain, "INVALID_CHANGE_CLAIM_DOMAIN")
        if not isinstance(self.impacted_entity_type, str) or not self.impacted_entity_type.strip() or not isinstance(self.impacted_entity_id, str) or not self.impacted_entity_id.strip():
            raise ValueError("INVALID_CHANGE_CLAIM_TARGET")
        if not isinstance(self.requires_application_approval, bool):
            raise ValueError("INVALID_CHANGE_CLAIM_APPROVAL_FLAG")
        if not self.schedule_reference and not self.cost_reference:
            raise ValueError("CHANGE_CLAIM_IMPACT_REFERENCE_REQUIRED")
        if not self.evidence_refs:
            raise ValueError("CHANGE_CLAIM_EVIDENCE_REQUIRED")
