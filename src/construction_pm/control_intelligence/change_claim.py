from dataclasses import dataclass, field
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference
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
        if self.record_type not in {"change", "claim"}:
            raise ValueError("INVALID_CHANGE_CLAIM_RECORD_TYPE")
        if not self.link_id or not self.record_id or not self.impact_type:
            raise ValueError("INVALID_CHANGE_CLAIM_IMPACT")
        if not self.impacted_entity_type or not self.impacted_entity_id:
            raise ValueError("INVALID_CHANGE_CLAIM_TARGET")
        if not self.schedule_reference and not self.cost_reference:
            raise ValueError("CHANGE_CLAIM_IMPACT_REFERENCE_REQUIRED")
        if not self.evidence_refs:
            raise ValueError("CHANGE_CLAIM_EVIDENCE_REQUIRED")
        if self.requires_application_approval and self.record_type == "claim" and not self.cost_reference and not self.schedule_reference:
            raise ValueError("CLAIM_APPROVAL_REFERENCE_REQUIRED")
