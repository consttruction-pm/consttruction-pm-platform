from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping, Tuple, TypeVar, Type

MAX_SAFE_REVISION = 9_007_199_254_740_991

from .graph import ControlDomain

E = TypeVar("E", bound=Enum)


def require_enum(value: object, enum_type: Type[E], error_code: str) -> None:
    if not isinstance(value, enum_type):
        raise ValueError(error_code)


@dataclass(frozen=True)
class ControlScope:
    tenant_id: str
    project_id: str
    project_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip() or not isinstance(self.project_id, str) or not self.project_id.strip():
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
        if not isinstance(self.source_id, str) or not self.source_id.strip() or not isinstance(self.source_type, str) or not self.source_type.strip() or not isinstance(self.locator, str) or not self.locator.strip():
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
        if not isinstance(self.finding_id, str) or not self.finding_id.strip() or not isinstance(self.title_key, str) or not self.title_key.strip() or not isinstance(self.detail_key, str) or not self.detail_key.strip():
            raise ValueError("INVALID_CONTROL_FINDING")
        require_enum(self.domain, ControlDomain, "INVALID_CONTROL_FINDING_DOMAIN")
        require_enum(self.severity, FindingSeverity, "INVALID_CONTROL_FINDING_SEVERITY")
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
        if not isinstance(self.action_id, str) or not self.action_id.strip() or not isinstance(self.action_type, str) or not self.action_type.strip() or not isinstance(self.title_key, str) or not self.title_key.strip():
            raise ValueError("INVALID_PROPOSED_ACTION")
        if not isinstance(self.requires_approval, bool):
            raise ValueError("INVALID_PROPOSED_ACTION_APPROVAL_FLAG")
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
        if not isinstance(self.result_id, str) or not self.result_id.strip() or not isinstance(self.summary_key, str) or not self.summary_key.strip():
            raise ValueError("INVALID_CONTROL_RESULT")
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_CONTROL_RESULT_SCOPE")
        if not isinstance(self.generated_at, datetime) or self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("CONTROL_RESULT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if not self.source_refs:
            raise ValueError("CONTROL_RESULT_SOURCE_REQUIRED")
