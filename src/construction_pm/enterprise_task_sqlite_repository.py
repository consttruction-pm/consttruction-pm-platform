"""SQLite persistence for CUBI Enterprise tasks.

The production runtime uses :class:`PostgresEnterpriseTaskRepository` with
advisory locks and row locks. The local full-stack preview owns a single
SQLite connection, so this adapter keeps the same invariants (tenant scope,
revision checks, idempotency, audit trail, dependency cycle rejection) while
serialising writes through the preview runtime lock.

This is a preview adapter, not a production concurrency implementation.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import datetime
from typing import Any

from .enterprise_task import EnterpriseTask, EnterpriseTaskStatus
from .enterprise_task_repository import (
    EnterpriseTaskAuditEvent,
    EnterpriseTaskDependencyError,
    EnterpriseTaskIdempotencyReuse,
    EnterpriseTaskNotFound,
    EnterpriseTaskRevisionConflict,
    StoredEnterpriseTask,
)


class SQLiteEnterpriseTaskRepository:
    """Tenant-scoped task persistence on the preview SQLite database."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS enterprise_tasks (
                tenant_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                task_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                PRIMARY KEY (tenant_id, task_id)
            );
            CREATE TABLE IF NOT EXISTS enterprise_task_idempotency (
                tenant_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                task_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                PRIMARY KEY (tenant_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS enterprise_task_dependencies (
                tenant_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                dependency_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, task_id, dependency_id)
            );
            CREATE TABLE IF NOT EXISTS enterprise_task_audit (
                tenant_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, task_id, revision)
            );
            """
        )
        self.connection.commit()

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
        try:
            existing = self.connection.execute(
                "SELECT task_id, fingerprint FROM enterprise_task_idempotency "
                "WHERE tenant_id=? AND idempotency_key=?",
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
            self.connection.execute(
                "INSERT INTO enterprise_tasks "
                "(tenant_id, task_id, revision, task_json, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (
                    task.tenant_id,
                    task.task_id,
                    1,
                    self._serialize(stored_task),
                    self._text(task.created_at),
                    self._text(task.updated_at),
                ),
            )
            self.connection.execute(
                "INSERT INTO enterprise_task_idempotency "
                "(tenant_id, idempotency_key, task_id, fingerprint) VALUES (?,?,?,?)",
                (task.tenant_id, idempotency_key, task.task_id, fingerprint),
            )
            self._replace_dependencies(task.tenant_id, task.task_id, task.dependency_ids)
            self._append_audit(task.tenant_id, task.task_id, 1, "created", actor_id, occurred_at)
            self.connection.commit()
            return StoredEnterpriseTask(stored_task, 1)
        except Exception:
            self.connection.rollback()
            raise

    def get(self, tenant_id: str, task_id: str) -> StoredEnterpriseTask:
        self._validate_scope(tenant_id, task_id)
        row = self.connection.execute(
            "SELECT task_json, revision FROM enterprise_tasks WHERE tenant_id=? AND task_id=?",
            (tenant_id, task_id),
        ).fetchone()
        if row is None:
            raise EnterpriseTaskNotFound("ENTERPRISE_TASK_NOT_FOUND")
        return self._stored(row, tenant_id)

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        limit: int = 100,
        before_updated_at: datetime | None = None,
        before_task_id: str | None = None,
        project_id: str | None = None,
        personal_user_id: str | None = None,
    ) -> tuple[StoredEnterpriseTask, ...]:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("INVALID_ENTERPRISE_TASK_TENANT_ID")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("INVALID_ENTERPRISE_TASK_PAGE_SIZE")
        if project_id is not None and personal_user_id is not None:
            raise ValueError("ENTERPRISE_TASK_LIST_SCOPE_AMBIGUOUS")
        where = ["tenant_id=?"]
        params: list[object] = [tenant_id]
        if project_id is not None:
            self._validate_scope(tenant_id, project_id)
            where.append("json_extract(task_json, '$.project_id') = ?")
            params.append(project_id)
        elif personal_user_id is not None:
            self._validate_scope(tenant_id, personal_user_id)
            where.extend(
                [
                    "json_extract(task_json, '$.project_id') IS NULL",
                    "(json_extract(task_json, '$.created_by_user_id') = ? "
                    "OR json_extract(task_json, '$.assigned_user_id') = ?)",
                ]
            )
            params.extend((personal_user_id, personal_user_id))
        if before_task_id is None:
            if before_updated_at is not None:
                raise ValueError("ENTERPRISE_TASK_PAGE_CURSOR_REQUIRES_TASK_ID")
        else:
            self._validate_scope(tenant_id, before_task_id)
            if before_updated_at is None:
                where.append("updated_at IS NULL AND task_id > ?")
                params.append(before_task_id)
            else:
                self._aware(before_updated_at, "PAGE_CURSOR")
                where.append(
                    "(updated_at < ? OR (updated_at = ? AND task_id > ?) OR updated_at IS NULL)"
                )
                params.extend(
                    (self._text(before_updated_at), self._text(before_updated_at), before_task_id)
                )
        params.append(limit)
        rows = self.connection.execute(
            "SELECT task_json, revision FROM enterprise_tasks WHERE "
            + " AND ".join(where)
            + " ORDER BY updated_at IS NULL, updated_at DESC, task_id ASC LIMIT ?",
            tuple(params),
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
        try:
            row = self.connection.execute(
                "SELECT task_json, revision FROM enterprise_tasks WHERE tenant_id=? AND task_id=?",
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
            if (
                next_task.status is EnterpriseTaskStatus.COMPLETED
                and current.status is not EnterpriseTaskStatus.COMPLETED
                and next_task.completed_by_user_id != actor_id
            ):
                raise ValueError("ENTERPRISE_TASK_COMPLETION_ACTOR_MISMATCH")
            self._validate_dependencies(task.tenant_id, task.task_id, task.dependency_ids)
            cursor = self.connection.execute(
                "UPDATE enterprise_tasks SET revision=?, task_json=?, updated_at=? "
                "WHERE tenant_id=? AND task_id=? AND revision=?",
                (
                    next_task.revision,
                    self._serialize(next_task),
                    self._text(occurred_at),
                    task.tenant_id,
                    task.task_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise EnterpriseTaskRevisionConflict("ENTERPRISE_TASK_REVISION_CONFLICT")
            self._replace_dependencies(task.tenant_id, task.task_id, task.dependency_ids)
            event_type = (
                "completed"
                if next_task.status is EnterpriseTaskStatus.COMPLETED
                and current.status is not EnterpriseTaskStatus.COMPLETED
                else "updated"
            )
            self._append_audit(
                task.tenant_id,
                task.task_id,
                next_task.revision,
                event_type,
                actor_id,
                occurred_at,
            )
            self.connection.commit()
            return StoredEnterpriseTask(next_task, next_task.revision)
        except Exception:
            self.connection.rollback()
            raise

    def history(self, tenant_id: str, task_id: str) -> tuple[EnterpriseTaskAuditEvent, ...]:
        self._validate_scope(tenant_id, task_id)
        rows = self.connection.execute(
            "SELECT revision, event_type, actor_id, occurred_at FROM enterprise_task_audit "
            "WHERE tenant_id=? AND task_id=? ORDER BY revision",
            (tenant_id, task_id),
        ).fetchall()
        return tuple(
            EnterpriseTaskAuditEvent(
                task_id,
                int(row[0]),
                str(row[1]),
                str(row[2]),
                datetime.fromisoformat(str(row[3])),
            )
            for row in rows
        )

    def _validate_dependencies(
        self, tenant_id: str, task_id: str, dependency_ids: tuple[str, ...]
    ) -> None:
        if not dependency_ids:
            return
        placeholders = ",".join("?" for _ in dependency_ids)
        rows = self.connection.execute(
            f"SELECT task_id FROM enterprise_tasks WHERE tenant_id=? AND task_id IN ({placeholders})",
            (tenant_id, *dependency_ids),
        ).fetchall()
        if {str(row[0]) for row in rows} != set(dependency_ids):
            raise EnterpriseTaskDependencyError(
                "ENTERPRISE_TASK_DEPENDENCY_NOT_FOUND_OR_OUT_OF_TENANT"
            )
        # Depth-first cycle check over tenant edges. The preview graph is small;
        # production keeps the recursive SQL + advisory lock implementation.
        edges: dict[str, set[str]] = {}
        for row in self.connection.execute(
            "SELECT task_id, dependency_id FROM enterprise_task_dependencies WHERE tenant_id=?",
            (tenant_id,),
        ):
            edges.setdefault(str(row[0]), set()).add(str(row[1]))
        stack = list(dependency_ids)
        seen: set[str] = set()
        while stack:
            node = stack.pop()
            if node == task_id:
                raise EnterpriseTaskDependencyError("ENTERPRISE_TASK_DEPENDENCY_CYCLE")
            if node in seen:
                continue
            seen.add(node)
            stack.extend(edges.get(node, ()))

    def _replace_dependencies(
        self, tenant_id: str, task_id: str, dependency_ids: tuple[str, ...]
    ) -> None:
        self.connection.execute(
            "DELETE FROM enterprise_task_dependencies WHERE tenant_id=? AND task_id=?",
            (tenant_id, task_id),
        )
        for dependency_id in dependency_ids:
            self.connection.execute(
                "INSERT INTO enterprise_task_dependencies (tenant_id, task_id, dependency_id) "
                "VALUES (?,?,?)",
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
            "VALUES (?,?,?,?,?,?)",
            (tenant_id, task_id, revision, event_type, actor_id, self._text(occurred_at)),
        )

    @classmethod
    def _stored(cls, row: Any, tenant_id: str) -> StoredEnterpriseTask:
        task = cls._deserialize(row[0])
        revision = int(row[1])
        if task.tenant_id != tenant_id or task.revision != revision:
            raise ValueError("ENTERPRISE_TASK_STORED_SCOPE_OR_REVISION_MISMATCH")
        return StoredEnterpriseTask(task, revision)

    @staticmethod
    def _serialize(task: EnterpriseTask) -> str:
        return json.dumps(task.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

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
        import hashlib

        payload = task.as_dict()
        for generated in ("task_id", "created_at", "updated_at", "revision"):
            payload.pop(generated, None)
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _text(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

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
        SQLiteEnterpriseTaskRepository._aware(occurred_at, "AUDIT_TIMESTAMP")

    @staticmethod
    def _aware(value: datetime, name: str) -> None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"ENTERPRISE_TASK_{name}_MUST_BE_TIMEZONE_AWARE")

    @staticmethod
    def _revision(value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("INVALID_ENTERPRISE_TASK_REVISION")
