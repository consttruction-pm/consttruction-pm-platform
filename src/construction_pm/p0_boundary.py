from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping

from .client_sync.revision_limits import MAX_SAFE_PROJECT_REVISION


@dataclass(frozen=True)
class ProjectContext:
    tenant_id: str
    project_id: str

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.project_id:
            raise ValueError("INVALID_PROJECT_CONTEXT")


@dataclass(frozen=True)
class RevisionPrecondition:
    context: ProjectContext
    expected_revision: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.expected_revision, bool)
            or not isinstance(self.expected_revision, int)
            or self.expected_revision < 0
            or self.expected_revision > MAX_SAFE_PROJECT_REVISION
        ):
            raise ValueError("INVALID_EXPECTED_REVISION")


@dataclass(frozen=True)
class AuditEvent:
    context: ProjectContext
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    revision: int
    metadata: Mapping[str, object] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.actor_id or not self.action or not self.resource_type or not self.resource_id:
            raise ValueError("INVALID_AUDIT_EVENT")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 0
            or self.revision > MAX_SAFE_PROJECT_REVISION
        ):
            raise ValueError("INVALID_AUDIT_REVISION")
        if self.occurred_at.tzinfo is None:
            raise ValueError("AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")


@dataclass(frozen=True)
class IdempotencyScope:
    context: ProjectContext
    key: str
    fingerprint: str

    def __post_init__(self) -> None:
        if not self.key or not self.fingerprint:
            raise ValueError("INVALID_IDEMPOTENCY_METADATA")

    @property
    def storage_key(self) -> tuple[str, str, str]:
        return (self.context.tenant_id, self.context.project_id, self.key)
