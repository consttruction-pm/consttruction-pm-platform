from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from .enterprise_task import EnterpriseTask, EnterpriseTaskStatus


class EnterpriseTaskNotFound(KeyError):
    pass


class EnterpriseTaskRevisionConflict(ValueError):
    pass


class EnterpriseTaskIdempotencyReuse(ValueError):
    pass


class EnterpriseTaskDependencyError(ValueError):
    pass


@dataclass(frozen=True)
class StoredEnterpriseTask:
    task: EnterpriseTask
    revision: int


@dataclass(frozen=True)
class EnterpriseTaskAuditEvent:
    task_id: str
    revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime


class PostgresEnterpriseTaskRepository:
    """Tenant-scoped task persistence; caller owns transaction boundaries."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_tasks (
                tenant_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                revision BIGINT NOT NULL,
                task_json TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ,
                PRIMARY KEY (tenant_id, task_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_task_idempotency (
                tenant_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                task_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                PRIMARY KEY (tenant_id, idempotency_key),
                FOREIGN KEY (tenant_id, task_id)
                    REFERENCES enterprise_tasks (tenant_id, task_id) ON DELETE CASCADE
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_task_dependencies (
                tenant_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                dependency_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, task_id, dependency_id),
                FOREIGN KEY (tenant_id, task_id)
                    REFERENCES enterprise_tasks (tenant_id, task_id) ON DELETE CASCADE,
                FOREIGN KEY (tenant_id, dependency_id)
                    REFERENCES enterprise_tasks (tenant_id, task_id) ON DELETE RESTRICT,
                CHECK (task_id <> dependency_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS enterprise_task_audit (
                tenant_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                revision BIGINT NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (tenant_id, task_id, revision),
                FOREIGN KEY (tenant_id, task_id)
                    REFERENCES enterprise_tasks (tenant_id, task_id) ON DELETE CASCADE
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_enterprise_tasks_assignee "
            "ON enterprise_tasks (tenant_id, updated_at DESC, task_id)"
        )

    def create(
        self,
        task: EnterpriseTask,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredEnterpriseTask:
        task.validate()
        self._validate_metadata(idempotency_key, actor_id, occurred_at)
        if actor_id != task.created_by_user_id:
            raise ValueError("ENTERPRISE_TASK_CREATOR_ACTOR_MISMATCH")
        if task.revision != 0:
            raise ValueError("ENTERPRISE_TASK_CREATE_REVISION_MUST_BE_ZERO")
        if occurred_at < task.created_at:
            raise ValueError("ENTERPRISE_TASK_AUDIT_BEFORE_CREATION")
        fingerprint = self._fingerprint(task)

        # Serialize a tenant's idempotency-key decision without taking a
        # process-local lock; this works across workers and server instances.
        lock_key = f"{task.tenant_id}:{idempotency_key}"
        self.connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,)
        )
        existing = self.connection.execute(
            "SELECT task_id, fingerprint FROM enterprise_task_idempotency "
            "WHERE tenant_id=%s AND idempotency_key=%s",
            (task.tenant_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            if str(existing[1]) != fingerprint:
                raise EnterpriseTaskIdempotencyReuse(
                    "ENTERPRISE_TASK_IDEMPOTENCY_KEY_REUSE"
                )
            return self.get(task.tenant_id, str(existing[0]))

        self._validate_dependencies(task.tenant_id, task.task_id, task.dependency_ids)
        stored_task = replace(task, revision=1)
        payload = self._serialize(stored_task)
        self.connection.execute(
            "INSERT INTO enterprise_tasks "
            "(tenant_id, task_id, revision, task_json, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (
                task.tenant_id, task.task_id, 1, payload,
                task.created_at, task.updated_at,
            ),
        )
        self.connection.execute(
            "INSERT INTO enterprise_task_idempotency "
            "(tenant_id, idempotency_key, task_id, fingerprint) VALUES (%s,%s,%s,%s)",
            (task.tenant_id, idempotency_key, task.task_id, fingerprint),
        )
        self._replace_dependencies(task.tenant_id, task.task_id, task.dependency_ids)
        self._append_audit(
            task.tenant_id, task.task_id, 1, "created", actor_id, occurred_at
        )
        return StoredEnterpriseTask(stored_task, 1)

    def get(self, tenant_id: str, task_id: str) -> StoredEnterpriseTask:
        self._validate_scope(tenant_id, task_id)
        row = self.connection.execute(
            "SELECT task_json, revision FROM enterprise_tasks "
            "WHERE tenant_id=%s AND task_id=%s",
            (tenant_id, task_id),
        ).fetchone()
        if row is None:
            raise EnterpriseTaskNotFound("ENTERPRISE_TASK_NOT_FOUND")
        task = self._deserialize(row[0])
        revision = int(row[1])
        if task.tenant_id != tenant_id or task.task_id != task_id or task.revision != revision:
            raise ValueError("ENTERPRISE_TASK_STORED_SCOPE_OR_REVISION_MISMATCH")
        return StoredEnterpriseTask(task, revision)

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        limit: int = 100,
        before_updated_at: datetime | None = None,
    ) -> tuple[StoredEnterpriseTask, ...]:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("INVALID_ENTERPRISE_TASK_TENANT_ID")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("INVALID_ENTERPRISE_TASK_PAGE_SIZE")
        if before_updated_at is not None:
            self._aware(before_updated_at, "PAGE_CURSOR")
            rows = self.connection.execute(
                "SELECT task_json, revision FROM enterprise_tasks "
                "WHERE tenant_id=%s AND updated_at < %s "
                "ORDER BY updated_at DESC NULLS LAST, task_id LIMIT %s",
                (tenant_id, before_updated_at, limit),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT task_json, revision FROM enterprise_tasks "
                "WHERE tenant_id=%s ORDER BY updated_at DESC NULLS LAST, task_id LIMIT %s",
                (tenant_id, limit),
            ).fetchall()
        return tuple(self._stored(row, tenant_id) for row in rows)

    def update(
        self,
        task: EnterpriseTask,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredEnterpriseTask:
        task.validate()
        self._validate_metadata("update", actor_id, occurred_at)
        self._revision(expected_revision)
        if task.revision != expected_revision:
            raise EnterpriseTaskRevisionConflict("ENTERPRISE_TASK_REVISION_CONFLICT")
        row = self.connection.execute(
            "SELECT task_json, revision FROM enterprise_tasks "
            "WHERE tenant_id=%s AND task_id=%s FOR UPDATE",
            (task.tenant_id, task.task_id),
        ).fetchone()
        if row is None:
            raise EnterpriseTaskNotFound("ENTERPRISE_TASK_NOT_FOUND")
        current = self._deserialize(row[0])
        current_revision = int(row[1])
        if current_revision != expected_revision:
            raise EnterpriseTaskRevisionConflict("ENTERPRISE_TASK_REVISION_CONFLICT")
        if (
            current.created_by_user_id != task.created_by_user_id
            or current.created_at != task.created_at
        ):
            raise ValueError("ENTERPRISE_TASK_IMMUTABLE_IDENTITY_MISMATCH")
        if occurred_at < current.created_at:
            raise ValueError("ENTERPRISE_TASK_AUDIT_BEFORE_CREATION")
        if task.updated_at is not None and task.updated_at != occurred_at:
            raise ValueError("ENTERPRISE_TASK_UPDATE_TIMESTAMP_MISMATCH")
        next_task = replace(task, revision=current_revision + 1, updated_at=occurred_at)
        next_task.validate()
        self._validate_dependencies(task.tenant_id, task.task_id, task.dependency_ids)
        self.connection.execute(
            "UPDATE enterprise_tasks SET revision=%s, task_json=%s, updated_at=%s "
            "WHERE tenant_id=%s AND task_id=%s AND revision=%s",
            (
                next_task.revision, self._serialize(next_task), occurred_at,
                task.tenant_id, task.task_id, expected_revision,
            ),
        )
        self._replace_dependencies(task.tenant_id, task.task_id, task.dependency_ids)
        event_type = (
            "completed"
            if next_task.status is EnterpriseTaskStatus.COMPLETED
            and current.status is not EnterpriseTaskStatus.COMPLETED
            else "updated"
        )
        self._append_audit(
            task.tenant_id, task.task_id, next_task.revision,
            event_type, actor_id, occurred_at,
        )
        return StoredEnterpriseTask(next_task, next_task.revision)

    def history(
        self, tenant_id: str, task_id: str
    ) -> tuple[EnterpriseTaskAuditEvent, ...]:
        self._validate_scope(tenant_id, task_id)
        rows = self.connection.execute(
            "SELECT revision, event_type, actor_id, occurred_at "
            "FROM enterprise_task_audit WHERE tenant_id=%s AND task_id=%s "
            "ORDER BY revision",
            (tenant_id, task_id),
        ).fetchall()
        return tuple(
            EnterpriseTaskAuditEvent(task_id, int(row[0]), str(row[1]), str(row[2]), row[3])
            for row in rows
        )

    def _validate_dependencies(
        self, tenant_id: str, task_id: str, dependency_ids: tuple[str, ...]
    ) -> None:
        if not dependency_ids:
            return
        rows = self.connection.execute(
            "SELECT task_id FROM enterprise_tasks "
            "WHERE tenant_id=%s AND task_id = ANY(%s)",
            (tenant_id, list(dependency_ids)),
        ).fetchall()
        found = {str(row[0]) for row in rows}
        if found != set(dependency_ids):
            raise EnterpriseTaskDependencyError(
                "ENTERPRISE_TASK_DEPENDENCY_NOT_FOUND_OR_OUT_OF_TENANT"
            )
        cycle = self.connection.execute(
            """WITH RECURSIVE reachable(task_id) AS (
                   SELECT unnest(%s::text[])
                   UNION
                   SELECT edge.dependency_id
                   FROM enterprise_task_dependencies AS edge
                   JOIN reachable ON edge.task_id = reachable.task_id
                   WHERE edge.tenant_id=%s
               )
               SELECT EXISTS (SELECT 1 FROM reachable WHERE task_id=%s)""",
            (list(dependency_ids), tenant_id, task_id),
        ).fetchone()
        if cycle is not None and bool(cycle[0]):
            raise EnterpriseTaskDependencyError("ENTERPRISE_TASK_DEPENDENCY_CYCLE")

    def _replace_dependencies(
        self, tenant_id: str, task_id: str, dependency_ids: tuple[str, ...]
    ) -> None:
        self.connection.execute(
            "DELETE FROM enterprise_task_dependencies WHERE tenant_id=%s AND task_id=%s",
            (tenant_id, task_id),
        )
        for dependency_id in dependency_ids:
            self.connection.execute(
                "INSERT INTO enterprise_task_dependencies "
                "(tenant_id, task_id, dependency_id) VALUES (%s,%s,%s)",
                (tenant_id, task_id, dependency_id),
            )

    def _append_audit(
        self,
        tenant_id: str,
        task_id: str,
        revision: int,
        event_type: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> None:
        self.connection.execute(
            "INSERT INTO enterprise_task_audit "
            "(tenant_id, task_id, revision, event_type, actor_id, occurred_at) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (tenant_id, task_id, revision, event_type, actor_id, occurred_at),
        )

    @staticmethod
    def _stored(row: Any, tenant_id: str) -> StoredEnterpriseTask:
        task = PostgresEnterpriseTaskRepository._deserialize(row[0])
        revision = int(row[1])
        if task.tenant_id != tenant_id or task.revision != revision:
            raise ValueError("ENTERPRISE_TASK_STORED_SCOPE_OR_REVISION_MISMATCH")
        return StoredEnterpriseTask(task, revision)

    @staticmethod
    def _serialize(task: EnterpriseTask) -> str:
        return json.dumps(
            task.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    @staticmethod
    def _deserialize(payload: str | dict[str, Any]) -> EnterpriseTask:
        data = json.loads(payload) if isinstance(payload, str) else payload
        from .enterprise_task import (
            EnterpriseTaskPriority,
            EnterpriseTaskReference,
            EnterpriseTaskReferenceType,
            EnterpriseTaskStatus,
        )

        task = EnterpriseTask(
            task_id=data["task_id"],
            tenant_id=data["tenant_id"],
            title=data["title"],
            created_by_user_id=data["created_by_user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=EnterpriseTaskStatus(data["status"]),
            priority=EnterpriseTaskPriority(data["priority"]),
            description=data.get("description"),
            assigned_user_id=data.get("assigned_user_id"),
            assigned_team_id=data.get("assigned_team_id"),
            project_id=data.get("project_id"),
            due_at=datetime.fromisoformat(data["due_at"]) if data.get("due_at") else None,
            dependency_ids=tuple(data.get("dependency_ids", ())),
            related_refs=tuple(
                EnterpriseTaskReference(
                    EnterpriseTaskReferenceType(ref["reference_type"]),
                    ref["reference_id"],
                    ref.get("revision"),
                )
                for ref in data.get("related_refs", ())
            ),
            revision=int(data["revision"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            completed_by_user_id=data.get("completed_by_user_id"),
        )
        task.validate()
        return task

    @staticmethod
    def _fingerprint(task: EnterpriseTask) -> str:
        return hashlib.sha256(
            PostgresEnterpriseTaskRepository._serialize(task).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _validate_scope(tenant_id: str, task_id: str) -> None:
        for name, value in (("TENANT_ID", tenant_id), ("TASK_ID", task_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_ENTERPRISE_TASK_{name}")

    @staticmethod
    def _validate_metadata(key: str, actor_id: str, occurred_at: datetime) -> None:
        if not isinstance(key, str) or not key.strip() or len(key) > 200:
            raise ValueError("INVALID_ENTERPRISE_TASK_IDEMPOTENCY_KEY")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("INVALID_ENTERPRISE_TASK_ACTOR")
        PostgresEnterpriseTaskRepository._aware(occurred_at, "AUDIT_TIMESTAMP")

    @staticmethod
    def _aware(value: datetime, name: str) -> None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"ENTERPRISE_TASK_{name}_MUST_BE_TIMEZONE_AWARE")

    @staticmethod
    def _revision(value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("INVALID_ENTERPRISE_TASK_REVISION")
