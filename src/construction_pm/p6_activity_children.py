"""Activity child collections that are not part of the schedule itself.

Version 26 keeps two child collections directly on an activity:

* Activity Code assignments (Project > Activity Codes / Details > Codes).
* Notebook topics (Details > Notebook). The topic body is HTML in the
  reference product; it is sanitised here to a small allow-list rather than
  stored or replayed verbatim.

Both collections are project-scoped, tenant-isolated application records.
They never feed the scheduling core and no scheduling value is derived from
them. Writes are optimistic: the record revision carried by the client must
match the stored revision, otherwise the caller gets REVISION_CONFLICT (409).
"""

from __future__ import annotations

import html
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope

ACTIVITY_CODE_API_VERSION = "p6-activity-code-api.v1"
ACTIVITY_NOTEBOOK_API_VERSION = "p6-activity-notebook-api.v1"

_ALLOWED_NOTEBOOK_TAGS = frozenset({"b", "strong", "i", "em", "u", "br", "p", "ul", "ol", "li"})


class ActivityChildPersistenceError(ValueError):
    """Raised when an activity child record is invalid or conflicts."""


class _NotebookSanitizer(HTMLParser):
    """Escape every tag except a short formatting allow-list."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _ALLOWED_NOTEBOOK_TAGS:
            self.parts.append(f"<{tag}>")
        else:
            # Keep the text, drop the element and all of its attributes.
            self.parts.append("")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _ALLOWED_NOTEBOOK_TAGS:
            self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in _ALLOWED_NOTEBOOK_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data, quote=True))

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&amp;{html.escape(name)};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        return


def sanitize_notebook_html(value: str) -> str:
    if not isinstance(value, str):
        raise ActivityChildPersistenceError("INVALID_NOTEBOOK_DESCRIPTION")
    parser = _NotebookSanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts).strip()


@dataclass(frozen=True)
class ActivityCodeAssignment:
    scope: BackendScope
    assignment_id: str
    activity_id: str
    code_type: str
    code_value: str
    description: str | None = None
    record_revision: int = 1
    created_at: str = ""
    updated_at: str = ""

    def validate(self) -> None:
        self.scope.validate()
        for value, code in (
            (self.assignment_id, "ASSIGNMENT_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.code_type, "CODE_TYPE"),
            (self.code_value, "CODE_VALUE"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ActivityChildPersistenceError(f"INVALID_{code}")
        if self.description is not None and not isinstance(self.description, str):
            raise ActivityChildPersistenceError("INVALID_DESCRIPTION")
        if not isinstance(self.record_revision, int) or isinstance(self.record_revision, bool) or self.record_revision < 1:
            raise ActivityChildPersistenceError("INVALID_RECORD_REVISION")


@dataclass(frozen=True)
class NotebookTopic:
    scope: BackendScope
    topic_id: str
    activity_id: str
    topic_name: str
    description: str = ""
    sequence: int = 0
    record_revision: int = 1
    created_at: str = ""
    updated_at: str = ""

    def validate(self) -> None:
        self.scope.validate()
        for value, code in (
            (self.topic_id, "TOPIC_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.topic_name, "TOPIC_NAME"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ActivityChildPersistenceError(f"INVALID_{code}")
        if not isinstance(self.description, str):
            raise ActivityChildPersistenceError("INVALID_NOTEBOOK_DESCRIPTION")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 0:
            raise ActivityChildPersistenceError("INVALID_SEQUENCE")
        if not isinstance(self.record_revision, int) or isinstance(self.record_revision, bool) or self.record_revision < 1:
            raise ActivityChildPersistenceError("INVALID_RECORD_REVISION")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SQLiteActivityChildrenRepository:
    """SQLite persistence for Activity Codes and Notebook topics."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_activity_code_assignment (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                assignment_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                code_type TEXT NOT NULL,
                code_value TEXT NOT NULL,
                description TEXT,
                record_revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, assignment_id)
            )"""
        )
        self.connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_p6_activity_code_type "
            "ON p6_activity_code_assignment(tenant_id, project_id, activity_id, code_type)"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_activity_notebook_topic (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                topic_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                description TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                record_revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, topic_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_activity_notebook_activity "
            "ON p6_activity_notebook_topic(tenant_id, project_id, activity_id, sequence, topic_id)"
        )
        self.connection.commit()

    # -- Activity Codes -------------------------------------------------
    def list_codes(self, scope: BackendScope, activity_id: str) -> tuple[ActivityCodeAssignment, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT assignment_id,activity_id,code_type,code_value,description,record_revision,created_at,updated_at "
            "FROM p6_activity_code_assignment WHERE tenant_id=? AND project_id=? AND activity_id=? "
            "ORDER BY code_type, assignment_id",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchall()
        return tuple(_code_from_row(scope, row) for row in rows)

    def assign_code(
        self,
        scope: BackendScope,
        activity_id: str,
        code_type: str,
        code_value: str,
        description: str | None,
    ) -> ActivityCodeAssignment:
        existing = self.connection.execute(
            "SELECT assignment_id,record_revision,created_at FROM p6_activity_code_assignment "
            "WHERE tenant_id=? AND project_id=? AND activity_id=? AND code_type=?",
            (scope.tenant_id, scope.project_id, activity_id, code_type),
        ).fetchone()
        now = _now()
        if existing is None:
            assignment = ActivityCodeAssignment(
                scope=scope,
                assignment_id=str(uuid.uuid4()),
                activity_id=activity_id,
                code_type=code_type,
                code_value=code_value,
                description=description,
                record_revision=1,
                created_at=now,
                updated_at=now,
            )
            assignment.validate()
            self.connection.execute(
                "INSERT INTO p6_activity_code_assignment "
                "(tenant_id,project_id,project_revision,assignment_id,activity_id,code_type,code_value,"
                "description,record_revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (scope.tenant_id, scope.project_id, scope.project_revision, assignment.assignment_id,
                 activity_id, code_type, code_value, description, 1, now, now),
            )
            self.connection.commit()
            return assignment
        assignment = ActivityCodeAssignment(
            scope=scope,
            assignment_id=str(existing[0]),
            activity_id=activity_id,
            code_type=code_type,
            code_value=code_value,
            description=description,
            record_revision=int(existing[1]) + 1,
            created_at=str(existing[2]),
            updated_at=now,
        )
        assignment.validate()
        self.connection.execute(
            "UPDATE p6_activity_code_assignment SET project_revision=?,code_value=?,description=?,"
            "record_revision=?,updated_at=? WHERE tenant_id=? AND project_id=? AND assignment_id=?",
            (scope.project_revision, code_value, description, assignment.record_revision, now,
             scope.tenant_id, scope.project_id, assignment.assignment_id),
        )
        self.connection.commit()
        return assignment

    def remove_code(self, scope: BackendScope, activity_id: str, assignment_id: str) -> bool:
        scope.validate()
        cursor = self.connection.execute(
            "DELETE FROM p6_activity_code_assignment "
            "WHERE tenant_id=? AND project_id=? AND activity_id=? AND assignment_id=?",
            (scope.tenant_id, scope.project_id, activity_id, assignment_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    # -- Notebook -------------------------------------------------------
    def list_topics(self, scope: BackendScope, activity_id: str) -> tuple[NotebookTopic, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT topic_id,activity_id,topic_name,description,sequence,record_revision,created_at,updated_at "
            "FROM p6_activity_notebook_topic WHERE tenant_id=? AND project_id=? AND activity_id=? "
            "ORDER BY sequence, topic_id",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchall()
        return tuple(_topic_from_row(scope, row) for row in rows)

    def add_topic(
        self, scope: BackendScope, activity_id: str, topic_name: str, description: str
    ) -> NotebookTopic:
        rows = self.connection.execute(
            "SELECT COALESCE(MAX(sequence),0) FROM p6_activity_notebook_topic "
            "WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchone()
        now = _now()
        topic = NotebookTopic(
            scope=scope,
            topic_id=str(uuid.uuid4()),
            activity_id=activity_id,
            topic_name=topic_name,
            description=sanitize_notebook_html(description),
            sequence=int(rows[0] or 0) + 1,
            record_revision=1,
            created_at=now,
            updated_at=now,
        )
        topic.validate()
        self.connection.execute(
            "INSERT INTO p6_activity_notebook_topic "
            "(tenant_id,project_id,project_revision,topic_id,activity_id,topic_name,description,"
            "sequence,record_revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (scope.tenant_id, scope.project_id, scope.project_revision, topic.topic_id, activity_id,
             topic.topic_name, topic.description, topic.sequence, 1, now, now),
        )
        self.connection.commit()
        return topic

    def update_topic(
        self,
        scope: BackendScope,
        activity_id: str,
        topic_id: str,
        topic_name: str,
        description: str,
        expected_record_revision: int,
    ) -> NotebookTopic:
        row = self.connection.execute(
            "SELECT topic_name,description,sequence,record_revision,created_at FROM p6_activity_notebook_topic "
            "WHERE tenant_id=? AND project_id=? AND activity_id=? AND topic_id=?",
            (scope.tenant_id, scope.project_id, activity_id, topic_id),
        ).fetchone()
        if row is None:
            raise ActivityChildPersistenceError("NOTEBOOK_TOPIC_NOT_FOUND")
        if int(row[3]) != expected_record_revision:
            raise ActivityChildPersistenceError("REVISION_CONFLICT")
        now = _now()
        topic = NotebookTopic(
            scope=scope,
            topic_id=topic_id,
            activity_id=activity_id,
            topic_name=topic_name,
            description=sanitize_notebook_html(description),
            sequence=int(row[2]),
            record_revision=expected_record_revision + 1,
            created_at=str(row[4]),
            updated_at=now,
        )
        topic.validate()
        self.connection.execute(
            "UPDATE p6_activity_notebook_topic SET project_revision=?,topic_name=?,description=?,"
            "record_revision=?,updated_at=? WHERE tenant_id=? AND project_id=? AND topic_id=?",
            (scope.project_revision, topic.topic_name, topic.description, topic.record_revision, now,
             scope.tenant_id, scope.project_id, topic_id),
        )
        self.connection.commit()
        return topic

    def delete_topic(
        self, scope: BackendScope, activity_id: str, topic_id: str, expected_record_revision: int
    ) -> bool:
        row = self.connection.execute(
            "SELECT record_revision FROM p6_activity_notebook_topic "
            "WHERE tenant_id=? AND project_id=? AND activity_id=? AND topic_id=?",
            (scope.tenant_id, scope.project_id, activity_id, topic_id),
        ).fetchone()
        if row is None:
            raise ActivityChildPersistenceError("NOTEBOOK_TOPIC_NOT_FOUND")
        if int(row[0]) != expected_record_revision:
            raise ActivityChildPersistenceError("REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM p6_activity_notebook_topic "
            "WHERE tenant_id=? AND project_id=? AND activity_id=? AND topic_id=?",
            (scope.tenant_id, scope.project_id, activity_id, topic_id),
        )
        self.connection.commit()
        return True


def _code_from_row(scope: BackendScope, row: tuple[object, ...]) -> ActivityCodeAssignment:
    record = ActivityCodeAssignment(
        scope=scope,
        assignment_id=str(row[0]),
        activity_id=str(row[1]),
        code_type=str(row[2]),
        code_value=str(row[3]),
        description=None if row[4] is None else str(row[4]),
        record_revision=int(row[5]),
        created_at=str(row[6]),
        updated_at=str(row[7]),
    )
    record.validate()
    return record


def _topic_from_row(scope: BackendScope, row: tuple[object, ...]) -> NotebookTopic:
    record = NotebookTopic(
        scope=scope,
        topic_id=str(row[0]),
        activity_id=str(row[1]),
        topic_name=str(row[2]),
        description=str(row[3]),
        sequence=int(row[4]),
        record_revision=int(row[5]),
        created_at=str(row[6]),
        updated_at=str(row[7]),
    )
    record.validate()
    return record


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


@dataclass(frozen=True)
class P6ActivityChildrenAPI:
    """Authorised Activity Code and Notebook operations for one project scope."""

    repository: SQLiteActivityChildrenRepository
    authorization_policy: AuthorizationPolicy

    def _allowed(self, auth_context: AuthorizationContext, permission: Permission) -> None:
        if not self.authorization_policy.is_allowed(auth_context, permission):
            raise AuthorizationError("ACTIVITY_CHILD_NOT_AUTHORIZED")

    # -- codes ----------------------------------------------------------
    def list_codes(
        self, scope: BackendScope, activity_id: str, *, auth_context: AuthorizationContext
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        self._allowed(auth_context, Permission.PROJECT_READ)
        _require_activity_id(activity_id)
        return {
            "contract_version": ACTIVITY_CODE_API_VERSION,
            "kind": "p6_activity_code_list",
            "activity_id": activity_id,
            "codes": [_code_dto(item) for item in self.repository.list_codes(scope, activity_id)],
        }

    def assign_code(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        code_type: str,
        code_value: str,
        description: str | None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        self._allowed(auth_context, Permission.PROJECT_WRITE)
        _require_activity_id(activity_id)
        stored = self.repository.assign_code(scope, activity_id, code_type.strip(), code_value.strip(), description)
        return {"contract_version": ACTIVITY_CODE_API_VERSION, "kind": "p6_activity_code", "code": _code_dto(stored)}

    def remove_code(
        self,
        scope: BackendScope,
        activity_id: str,
        assignment_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        self._allowed(auth_context, Permission.PROJECT_WRITE)
        _require_activity_id(activity_id)
        if not assignment_id.strip():
            raise ActivityChildPersistenceError("INVALID_ASSIGNMENT_ID")
        if not self.repository.remove_code(scope, activity_id, assignment_id):
            raise ActivityChildPersistenceError("ACTIVITY_CODE_NOT_FOUND")
        return {
            "contract_version": ACTIVITY_CODE_API_VERSION,
            "kind": "p6_activity_code_delete",
            "assignment_id": assignment_id,
            "deleted": True,
        }

    # -- notebook -------------------------------------------------------
    def list_notebook(
        self, scope: BackendScope, activity_id: str, *, auth_context: AuthorizationContext
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        self._allowed(auth_context, Permission.PROJECT_READ)
        _require_activity_id(activity_id)
        return {
            "contract_version": ACTIVITY_NOTEBOOK_API_VERSION,
            "kind": "p6_activity_notebook_list",
            "activity_id": activity_id,
            "topics": [_topic_dto(item) for item in self.repository.list_topics(scope, activity_id)],
        }

    def add_topic(
        self,
        scope: BackendScope,
        activity_id: str,
        *,
        topic_name: str,
        description: str,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        self._allowed(auth_context, Permission.PROJECT_WRITE)
        _require_activity_id(activity_id)
        stored = self.repository.add_topic(scope, activity_id, topic_name.strip(), description)
        return {"contract_version": ACTIVITY_NOTEBOOK_API_VERSION, "kind": "p6_activity_notebook_topic", "topic": _topic_dto(stored)}

    def update_topic(
        self,
        scope: BackendScope,
        activity_id: str,
        topic_id: str,
        *,
        topic_name: str,
        description: str,
        expected_record_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        self._allowed(auth_context, Permission.PROJECT_WRITE)
        _require_activity_id(activity_id)
        stored = self.repository.update_topic(
            scope, activity_id, topic_id, topic_name.strip(), description, expected_record_revision
        )
        return {"contract_version": ACTIVITY_NOTEBOOK_API_VERSION, "kind": "p6_activity_notebook_topic", "topic": _topic_dto(stored)}

    def delete_topic(
        self,
        scope: BackendScope,
        activity_id: str,
        topic_id: str,
        *,
        expected_record_revision: int,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        self._allowed(auth_context, Permission.PROJECT_WRITE)
        _require_activity_id(activity_id)
        self.repository.delete_topic(scope, activity_id, topic_id, expected_record_revision)
        return {
            "contract_version": ACTIVITY_NOTEBOOK_API_VERSION,
            "kind": "p6_activity_notebook_delete",
            "topic_id": topic_id,
            "deleted": True,
        }


def _require_activity_id(activity_id: str) -> None:
    if not isinstance(activity_id, str) or not activity_id.strip():
        raise ActivityChildPersistenceError("INVALID_ACTIVITY_ID")


def _code_dto(item: ActivityCodeAssignment) -> dict[str, Any]:
    return {
        "assignment_id": item.assignment_id,
        "activity_id": item.activity_id,
        "code_type": item.code_type,
        "code_value": item.code_value,
        "description": item.description,
        "record_revision": item.record_revision,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _topic_dto(item: NotebookTopic) -> dict[str, Any]:
    return {
        "topic_id": item.topic_id,
        "activity_id": item.activity_id,
        "topic_name": item.topic_name,
        "description": item.description,
        "sequence": item.sequence,
        "record_revision": item.record_revision,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


__all__ = [
    "ACTIVITY_CODE_API_VERSION",
    "ACTIVITY_NOTEBOOK_API_VERSION",
    "ActivityChildPersistenceError",
    "ActivityCodeAssignment",
    "NotebookTopic",
    "P6ActivityChildrenAPI",
    "SQLiteActivityChildrenRepository",
    "sanitize_notebook_html",
]
