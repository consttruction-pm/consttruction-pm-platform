from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

MAX_SAFE_REVISION = 9_007_199_254_740_991


class EnterpriseTaskError(ValueError):
    """Invalid Enterprise task data or lifecycle metadata."""


class EnterpriseTaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EnterpriseTaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EnterpriseTaskReferenceType(str, Enum):
    ENGINEERING_ACTIVITY = "engineering_activity"
    WBS = "wbs"
    DOCUMENT = "document"
    RISK = "risk"


@dataclass(frozen=True)
class EnterpriseTaskReference:
    """Opaque link to a separately authorized source object."""

    reference_type: EnterpriseTaskReferenceType
    reference_id: str
    revision: int | None = None

    def validate(self) -> None:
        if not isinstance(self.reference_type, EnterpriseTaskReferenceType):
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_REFERENCE_TYPE")
        _required_text(self.reference_id, "REFERENCE_ID", maximum=200)
        if self.revision is not None:
            _revision(self.revision, "REFERENCE_REVISION")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "reference_type": self.reference_type.value,
            "reference_id": self.reference_id,
            "revision": self.revision,
        }


@dataclass(frozen=True)
class EnterpriseTask:
    task_id: str
    tenant_id: str
    title: str
    created_by_user_id: str
    created_at: datetime
    status: EnterpriseTaskStatus = EnterpriseTaskStatus.OPEN
    priority: EnterpriseTaskPriority = EnterpriseTaskPriority.NORMAL
    description: str | None = None
    assigned_user_id: str | None = None
    assigned_team_id: str | None = None
    project_id: str | None = None
    due_at: datetime | None = None
    dependency_ids: tuple[str, ...] = ()
    related_refs: tuple[EnterpriseTaskReference, ...] = ()
    revision: int = 0
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    completed_by_user_id: str | None = None

    def validate(self) -> None:
        _required_text(self.task_id, "TASK_ID", maximum=200)
        _required_text(self.tenant_id, "TENANT_ID", maximum=200)
        _required_text(self.title, "TITLE", maximum=500)
        _required_text(self.created_by_user_id, "CREATED_BY_USER_ID", maximum=200)
        if self.description is not None and (
            not isinstance(self.description, str) or len(self.description) > 10_000
        ):
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_DESCRIPTION")
        if not isinstance(self.status, EnterpriseTaskStatus):
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_STATUS")
        if not isinstance(self.priority, EnterpriseTaskPriority):
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_PRIORITY")
        _aware_datetime(self.created_at, "CREATED_AT")
        if self.due_at is not None:
            _aware_datetime(self.due_at, "DUE_AT")
        if self.updated_at is not None:
            _aware_datetime(self.updated_at, "UPDATED_AT")
            if self.updated_at < self.created_at:
                raise EnterpriseTaskError("ENTERPRISE_TASK_UPDATED_BEFORE_CREATED")
        for value, name in (
            (self.assigned_user_id, "ASSIGNED_USER_ID"),
            (self.assigned_team_id, "ASSIGNED_TEAM_ID"),
            (self.project_id, "PROJECT_ID"),
            (self.completed_by_user_id, "COMPLETED_BY_USER_ID"),
        ):
            if value is not None:
                _required_text(value, name, maximum=200)
        if self.assigned_user_id is not None and self.assigned_team_id is not None:
            raise EnterpriseTaskError("ENTERPRISE_TASK_MULTIPLE_ASSIGNEES")
        _revision(self.revision, "REVISION")
        if not isinstance(self.dependency_ids, tuple):
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_DEPENDENCIES")
        for dependency_id in self.dependency_ids:
            _required_text(dependency_id, "DEPENDENCY_ID", maximum=200)
        if self.task_id in self.dependency_ids:
            raise EnterpriseTaskError("ENTERPRISE_TASK_SELF_DEPENDENCY")
        if len(set(self.dependency_ids)) != len(self.dependency_ids):
            raise EnterpriseTaskError("DUPLICATE_ENTERPRISE_TASK_DEPENDENCY")
        if not isinstance(self.related_refs, tuple):
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_REFERENCES")
        seen_refs: set[tuple[str, str, int | None]] = set()
        for reference in self.related_refs:
            if not isinstance(reference, EnterpriseTaskReference):
                raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_REFERENCE")
            reference.validate()
            key = (reference.reference_type.value, reference.reference_id, reference.revision)
            if key in seen_refs:
                raise EnterpriseTaskError("DUPLICATE_ENTERPRISE_TASK_REFERENCE")
            seen_refs.add(key)
        if self.status is EnterpriseTaskStatus.COMPLETED:
            if self.completed_at is None or self.completed_by_user_id is None:
                raise EnterpriseTaskError("ENTERPRISE_TASK_COMPLETION_METADATA_REQUIRED")
            _aware_datetime(self.completed_at, "COMPLETED_AT")
            if self.completed_at < self.created_at:
                raise EnterpriseTaskError("ENTERPRISE_TASK_COMPLETED_BEFORE_CREATED")
        elif self.completed_at is not None or self.completed_by_user_id is not None:
            raise EnterpriseTaskError("ENTERPRISE_TASK_COMPLETION_METADATA_NOT_ALLOWED")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "contract_version": "cubi-enterprise-task.v1",
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "priority": self.priority.value,
            "assigned_user_id": self.assigned_user_id,
            "assigned_team_id": self.assigned_team_id,
            "project_id": self.project_id,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "dependency_ids": list(self.dependency_ids),
            "related_refs": [reference.as_dict() for reference in self.related_refs],
            "revision": self.revision,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed_by_user_id": self.completed_by_user_id,
        }


def _required_text(value: object, name: str, *, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise EnterpriseTaskError(f"INVALID_ENTERPRISE_TASK_{name}")


def _revision(value: object, name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= MAX_SAFE_REVISION
    ):
        raise EnterpriseTaskError(f"INVALID_ENTERPRISE_TASK_{name}")


def _aware_datetime(value: object, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EnterpriseTaskError(f"ENTERPRISE_TASK_{name}_MUST_BE_TIMEZONE_AWARE")
