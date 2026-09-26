from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping, Tuple

MAX_SAFE_REVISION = 9_007_199_254_740_991

from .graph import ControlDomain

@dataclass(frozen=True)
class ControlScope:
    tenant_id: str
    project_id: str
    project_revision: int

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.project_id:
            raise ValueError("INVALID_CONTROL_SCOPE")
        if (
            isinstance(self.project_revision, bool)
            or not isinstance(self.project_revision, int)
            or not 0 <= self.project_revision <= MAX_SAFE_REVISION
        ):
            raise ValueError("INVALID_PROJECT_REVISION")

@dataclass(frozen=True)
class SourceReference:
    source_id: str
    source_type: str
    locator: str
    revision: int
    excerpt_key: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_type or not self.locator:
            raise ValueError("INVALID_SOURCE_REFERENCE")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or not 0 <= self.revision <= MAX_SAFE_REVISION
        ):
            raise ValueError("INVALID_SOURCE_REVISION")

class FindingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass(frozen=True)
class ControlFinding:
    finding_id: str
    domain: ControlDomain
    severity: FindingSeverity
    title_key: str
    detail_key: str
    source_refs: Tuple[SourceReference, ...] = ()

    def __post_init__(self) -> None:
        if not self.finding_id or not self.title_key or not self.detail_key:
            raise ValueError("INVALID_CONTROL_FINDING")
        if not self.source_refs:
            raise ValueError("CONTROL_FINDING_SOURCE_REQUIRED")

@dataclass(frozen=True)
class ProposedAction:
    action_id: str
    action_type: str
    title_key: str
    source_refs: Tuple[SourceReference, ...] = ()
    requires_approval: bool = True

    def __post_init__(self) -> None:
        if not self.action_id or not self.action_type or not self.title_key:
            raise ValueError("INVALID_PROPOSED_ACTION")
        if self.requires_approval and not self.source_refs:
            raise ValueError("APPROVAL_ACTION_SOURCE_REQUIRED")

@dataclass(frozen=True)
class ControlIntelligenceResult:
    result_id: str
    scope: ControlScope
    generated_at: datetime
    summary_key: str
    findings: Tuple[ControlFinding, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)
    source_refs: Tuple[SourceReference, ...] = ()
    proposed_actions: Tuple[ProposedAction, ...] = ()

    def __post_init__(self) -> None:
        if not self.result_id or not self.summary_key:
            raise ValueError("INVALID_CONTROL_RESULT")
        if self.generated_at.tzinfo is None:
            raise ValueError("CONTROL_RESULT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if not self.source_refs:
            raise ValueError("CONTROL_RESULT_SOURCE_REQUIRED")
