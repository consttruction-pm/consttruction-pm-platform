from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Mapping
from uuid import uuid4

from .application.authorization import Permission
from .application.project_lifecycle import ProjectLifecycleError
from .enterprise_task import (
    EnterpriseTask,
    EnterpriseTaskError,
    EnterpriseTaskPriority,
    EnterpriseTaskStatus,
)
from .enterprise_task_repository import (
    EnterpriseTaskDependencyError,
    EnterpriseTaskNotFound,
    PostgresEnterpriseTaskRepository,
    StoredEnterpriseTask,
)


class EnterpriseTaskAuthorizationError(PermissionError):
    """The authenticated actor is outside the task's authorized scope."""


class EnterpriseTaskApplicationService:
    """Authenticated application boundary for personal and project tasks.

    Team assignment and Engineering object references remain closed until the
    organization-membership and cross-environment authorization adapters exist.
    """

    def __init__(self, repository: PostgresEnterpriseTaskRepository, lifecycle_api: object, *, clock=None) -> None:
        self._repository = repository
        self._lifecycle = lifecycle_api
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def list_tasks(
        self,
        session_id: str,
        *,
        project_id: str | None = None,
        limit: int = 100,
        before_updated_at: datetime | None = None,
        before_task_id: str | None = None,
    ) -> tuple[StoredEnterpriseTask, ...]:
        session = self._session(session_id)
        if project_id is not None:
            self._authorize_project(session_id, session.tenant_id, project_id, Permission.PROJECT_READ)
            return self._repository.list_for_tenant(
                session.tenant_id,
                limit=limit,
                before_updated_at=before_updated_at,
                before_task_id=before_task_id,
                project_id=project_id,
            )
        return self._repository.list_for_tenant(
            session.tenant_id,
            limit=limit,
            before_updated_at=before_updated_at,
            before_task_id=before_task_id,
            personal_user_id=session.user_id,
        )

    def get_task(self, session_id: str, task_id: str) -> StoredEnterpriseTask:
        session = self._session(session_id)
        stored = self._repository.get(session.tenant_id, task_id)
        self._authorize_task(session_id, session, stored.task, write=False)
        return stored

    def create_task(
        self,
        session_id: str,
        payload: Mapping[str, object],
        *,
        idempotency_key: str,
    ) -> StoredEnterpriseTask:
        session = self._session(session_id)
        if not isinstance(payload, Mapping):
            raise EnterpriseTaskError("ENTERPRISE_TASK_REQUEST_INVALID")
        project_id = self._optional_text(payload.get("project_id"), "PROJECT_ID")
        if project_id is not None:
            self._authorize_project(session_id, session.tenant_id, project_id, Permission.PROJECT_WRITE)
        assigned_team_id = self._optional_text(payload.get("assigned_team_id"), "ASSIGNED_TEAM_ID")
        if assigned_team_id is not None:
            raise EnterpriseTaskError("ENTERPRISE_TASK_TEAM_ASSIGNMENT_NOT_AVAILABLE")
        assigned_user_id = self._optional_text(payload.get("assigned_user_id"), "ASSIGNED_USER_ID")
        if project_id is None:
            if assigned_user_id not in (None, session.user_id):
                raise EnterpriseTaskAuthorizationError("PERSONAL_TASK_ASSIGNMENT_DENIED")
            assigned_user_id = session.user_id
        elif assigned_user_id not in (None, session.user_id):
            raise EnterpriseTaskAuthorizationError("PROJECT_TASK_ASSIGNMENT_DENIED")
        related_refs = payload.get("related_refs", ())
        if related_refs not in (None, (), []):
            raise EnterpriseTaskError("ENTERPRISE_TASK_REFERENCE_AUTHORIZATION_NOT_AVAILABLE")
        dependencies = self._string_tuple(payload.get("dependency_ids", ()), "DEPENDENCY_IDS")
        now = self._now()
        task = EnterpriseTask(
            task_id=f"task-{uuid4().hex}",
            tenant_id=session.tenant_id,
            title=self._required_text(payload.get("title"), "TITLE"),
            description=payload.get("description"),
            created_by_user_id=session.user_id,
            created_at=now,
            status=EnterpriseTaskStatus.OPEN,
            priority=self._priority(payload.get("priority", EnterpriseTaskPriority.NORMAL.value)),
            assigned_user_id=assigned_user_id,
            project_id=project_id,
            due_at=self._datetime(payload.get("due_at"), "DUE_AT"),
            dependency_ids=dependencies,
        )
        task.validate()
        self._validate_dependency_scope(session, task, dependencies)
        return self._repository.create(
            task,
            idempotency_key=idempotency_key,
            actor_id=session.user_id,
            occurred_at=now,
        )

    def update_task(
        self,
        session_id: str,
        task_id: str,
        payload: Mapping[str, object],
    ) -> StoredEnterpriseTask:
        session = self._session(session_id)
        if not isinstance(payload, Mapping):
            raise EnterpriseTaskError("ENTERPRISE_TASK_REQUEST_INVALID")
        current = self._repository.get(session.tenant_id, task_id)
        self._authorize_task(session_id, session, current.task, write=True)
        expected_revision = payload.get("expected_revision")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise EnterpriseTaskError("ENTERPRISE_TASK_EXPECTED_REVISION_REQUIRED")
        if expected_revision != current.revision:
            from .enterprise_task_repository import EnterpriseTaskRevisionConflict
            raise EnterpriseTaskRevisionConflict("ENTERPRISE_TASK_REVISION_CONFLICT")
        immutable = ("task_id", "tenant_id", "created_by_user_id", "created_at", "project_id")
        for field in immutable:
            if field in payload and payload[field] != getattr(current.task, field):
                raise EnterpriseTaskError(f"ENTERPRISE_TASK_{field.upper()}_IMMUTABLE")
        if payload.get("assigned_team_id") is not None:
            raise EnterpriseTaskError("ENTERPRISE_TASK_TEAM_ASSIGNMENT_NOT_AVAILABLE")
        if payload.get("related_refs") not in (None, (), []):
            raise EnterpriseTaskError("ENTERPRISE_TASK_REFERENCE_AUTHORIZATION_NOT_AVAILABLE")
        changes: dict[str, object] = {}
        if "title" in payload:
            changes["title"] = self._required_text(payload["title"], "TITLE")
        if "description" in payload:
            changes["description"] = payload["description"]
        if "priority" in payload:
            changes["priority"] = self._priority(payload["priority"])
        if "status" in payload:
            changes["status"] = self._status(payload["status"])
        if "assigned_user_id" in payload:
            assigned = self._optional_text(payload["assigned_user_id"], "ASSIGNED_USER_ID")
            if assigned not in (None, session.user_id):
                raise EnterpriseTaskAuthorizationError("TASK_ASSIGNMENT_DENIED")
            changes["assigned_user_id"] = assigned
        if "due_at" in payload:
            changes["due_at"] = self._datetime(payload["due_at"], "DUE_AT")
        if "dependency_ids" in payload:
            dependencies = self._string_tuple(payload["dependency_ids"], "DEPENDENCY_IDS")
            self._validate_dependency_scope(session, current.task, dependencies)
            changes["dependency_ids"] = dependencies
        if not changes:
            raise EnterpriseTaskError("ENTERPRISE_TASK_NO_MUTABLE_FIELDS")
        next_status = changes.get("status", current.task.status)
        now = self._now()
        if next_status is EnterpriseTaskStatus.COMPLETED:
            if current.task.status is not EnterpriseTaskStatus.COMPLETED:
                changes["completed_at"] = now
                changes["completed_by_user_id"] = session.user_id
        else:
            changes["completed_at"] = None
            changes["completed_by_user_id"] = None
        updated = replace(current.task, revision=expected_revision, **changes)
        updated.validate()
        return self._repository.update(
            updated,
            expected_revision=expected_revision,
            actor_id=session.user_id,
            occurred_at=now,
        )

    def _session(self, session_id: str):
        if not isinstance(session_id, str) or not session_id:
            raise EnterpriseTaskAuthorizationError("SESSION_REQUIRED")
        return self._lifecycle.get_session(session_id, now=self._now())

    def _authorize_project(self, session_id: str, tenant_id: str, project_id: str, permission: Permission) -> None:
        try:
            context = self._lifecycle.authorize_project(
                session_id, project_id, permission, now=self._now()
            ).context
        except ProjectLifecycleError as exc:
            raise EnterpriseTaskAuthorizationError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED") from exc
        if context.tenant_id != tenant_id or context.project_id != project_id:
            raise EnterpriseTaskAuthorizationError("CROSS_SCOPE_ACCESS")

    def _authorize_task(self, session_id: str, session: object, task: EnterpriseTask, *, write: bool) -> None:
        if task.project_id is not None:
            self._authorize_project(
                session_id,
                session.tenant_id,
                task.project_id,
                Permission.PROJECT_WRITE if write else Permission.PROJECT_READ,
            )
            return
        if task.created_by_user_id != session.user_id:
            raise EnterpriseTaskNotFound("ENTERPRISE_TASK_NOT_FOUND")
        if task.assigned_user_id not in (None, session.user_id):
            raise EnterpriseTaskNotFound("ENTERPRISE_TASK_NOT_FOUND")

    def _validate_dependency_scope(self, session: object, task: EnterpriseTask, dependencies: tuple[str, ...]) -> None:
        for dependency_id in dependencies:
            dependency = self._repository.get(session.tenant_id, dependency_id).task
            if dependency.project_id != task.project_id:
                raise EnterpriseTaskDependencyError("ENTERPRISE_TASK_DEPENDENCY_SCOPE_MISMATCH")
            if task.project_id is None and dependency.created_by_user_id != session.user_id:
                raise EnterpriseTaskDependencyError("ENTERPRISE_TASK_DEPENDENCY_SCOPE_MISMATCH")

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise EnterpriseTaskError("ENTERPRISE_TASK_CLOCK_MUST_BE_TIMEZONE_AWARE")
        return value

    @staticmethod
    def _required_text(value: object, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise EnterpriseTaskError(f"INVALID_ENTERPRISE_TASK_{name}")
        return value.strip()

    @staticmethod
    def _optional_text(value: object, name: str) -> str | None:
        if value is None or value == "":
            return None
        if not isinstance(value, str) or not value.strip():
            raise EnterpriseTaskError(f"INVALID_ENTERPRISE_TASK_{name}")
        return value.strip()

    @staticmethod
    def _string_tuple(value: object, name: str) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise EnterpriseTaskError(f"INVALID_ENTERPRISE_TASK_{name}")
        return tuple(item.strip() for item in value)

    @staticmethod
    def _datetime(value: object, name: str) -> datetime | None:
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise EnterpriseTaskError(f"INVALID_ENTERPRISE_TASK_{name}")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise EnterpriseTaskError(f"INVALID_ENTERPRISE_TASK_{name}") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise EnterpriseTaskError(f"ENTERPRISE_TASK_{name}_MUST_BE_TIMEZONE_AWARE")
        return parsed

    @staticmethod
    def _priority(value: object) -> EnterpriseTaskPriority:
        try:
            return EnterpriseTaskPriority(value)
        except (TypeError, ValueError) as exc:
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_PRIORITY") from exc

    @staticmethod
    def _status(value: object) -> EnterpriseTaskStatus:
        try:
            return EnterpriseTaskStatus(value)
        except (TypeError, ValueError) as exc:
            raise EnterpriseTaskError("INVALID_ENTERPRISE_TASK_STATUS") from exc
