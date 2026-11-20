"""Project-level attachments drawn on the Gantt chart.

Version 26 records three attachment kinds on the bar chart:

* ``curtain`` — a date range shaded behind the bars;
* ``text`` — formatted text placed at a date, optionally tied to an activity;
* ``notebook`` — a link from a Notebook topic to an activity's bar. The topic
  body itself stays in the Notebook collection; this record only stores the
  link and the label shown on the bar.

These are presentation records. They never change schedule dates, durations,
float, progress or cost, and they are tenant/project isolated with an optimistic
record revision.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope

GANTT_ATTACHMENT_API_VERSION = "p6-gantt-attachment-api.v1"

KINDS = ("curtain", "text", "notebook")
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class GanttAttachmentPersistenceError(ValueError):
    """Raised when an attachment is invalid, missing or conflicts."""


def _iso_date(value: object, field: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise GanttAttachmentPersistenceError(f"INVALID_{field.upper()}")
    try:
        date.fromisoformat(value[:10])
    except ValueError as exc:
        raise GanttAttachmentPersistenceError(f"INVALID_{field.upper()}") from exc
    return value[:10]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class GanttAttachment:
    scope: BackendScope
    attachment_id: str
    kind: str
    label: str
    start_date: str | None = None
    end_date: str | None = None
    color: str | None = None
    activity_id: str | None = None
    topic_id: str | None = None
    visible: bool = True
    record_revision: int = 1
    created_at: str = ""
    updated_at: str = ""

    def validate(self) -> None:
        self.scope.validate()
        if self.kind not in KINDS:
            raise GanttAttachmentPersistenceError("INVALID_ATTACHMENT_KIND")
        if not isinstance(self.attachment_id, str) or not self.attachment_id.strip():
            raise GanttAttachmentPersistenceError("INVALID_ATTACHMENT_ID")
        if not isinstance(self.label, str) or not self.label.strip():
            raise GanttAttachmentPersistenceError("INVALID_LABEL")
        if self.color is not None and not _COLOR.match(self.color):
            raise GanttAttachmentPersistenceError("INVALID_COLOR")
        if self.kind == "curtain":
            if not self.start_date or not self.end_date:
                raise GanttAttachmentPersistenceError("CURTAIN_RANGE_REQUIRED")
            if self.start_date > self.end_date:
                raise GanttAttachmentPersistenceError("INVALID_CURTAIN_RANGE")
        if self.kind in ("text", "notebook"):
            if not self.activity_id:
                raise GanttAttachmentPersistenceError("ACTIVITY_REQUIRED")
        if self.kind == "notebook" and not self.topic_id:
            raise GanttAttachmentPersistenceError("TOPIC_REQUIRED")
        if not isinstance(self.visible, bool):
            raise GanttAttachmentPersistenceError("INVALID_VISIBLE")
        if not isinstance(self.record_revision, int) or isinstance(self.record_revision, bool) or self.record_revision < 1:
            raise GanttAttachmentPersistenceError("INVALID_RECORD_REVISION")


class SQLiteGanttAttachmentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS p6_gantt_attachment (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                attachment_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                label TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                color TEXT,
                activity_id TEXT,
                topic_id TEXT,
                visible INTEGER NOT NULL,
                record_revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, attachment_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_gantt_attachment_kind "
            "ON p6_gantt_attachment(tenant_id, project_id, kind, start_date)"
        )
        self.connection.commit()

    def list(self, scope: BackendScope) -> tuple[GanttAttachment, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT attachment_id,kind,label,start_date,end_date,color,activity_id,topic_id,"
            "visible,record_revision,created_at,updated_at FROM p6_gantt_attachment "
            "WHERE tenant_id=? AND project_id=? ORDER BY kind,start_date,attachment_id",
            (scope.tenant_id, scope.project_id),
        ).fetchall()
        return tuple(_from_row(scope, row) for row in rows)

    def create(self, scope: BackendScope, attachment: GanttAttachment) -> GanttAttachment:
        attachment.validate()
        exists = self.connection.execute(
            "SELECT 1 FROM p6_gantt_attachment WHERE tenant_id=? AND project_id=? AND attachment_id=?",
            (scope.tenant_id, scope.project_id, attachment.attachment_id),
        ).fetchone()
        if exists is not None:
            raise GanttAttachmentPersistenceError("ATTACHMENT_ALREADY_EXISTS")
        now = _now()
        created = GanttAttachment(**{**attachment.__dict__, "record_revision": 1, "created_at": now, "updated_at": now})
        self.connection.execute(
            "INSERT INTO p6_gantt_attachment (tenant_id,project_id,project_revision,attachment_id,kind,label,"
            "start_date,end_date,color,activity_id,topic_id,visible,record_revision,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (scope.tenant_id, scope.project_id, scope.project_revision, created.attachment_id, created.kind,
             created.label, created.start_date, created.end_date, created.color, created.activity_id,
             created.topic_id, 1 if created.visible else 0, 1, now, now),
        )
        self.connection.commit()
        return created

    def update(self, scope: BackendScope, attachment: GanttAttachment, expected_revision: int) -> GanttAttachment:
        attachment.validate()
        row = self.connection.execute(
            "SELECT record_revision,created_at FROM p6_gantt_attachment "
            "WHERE tenant_id=? AND project_id=? AND attachment_id=?",
            (scope.tenant_id, scope.project_id, attachment.attachment_id),
        ).fetchone()
        if row is None:
            raise GanttAttachmentPersistenceError("ATTACHMENT_NOT_FOUND")
        if int(row[0]) != expected_revision:
            raise GanttAttachmentPersistenceError("REVISION_CONFLICT")
        now = _now()
        updated = GanttAttachment(**{**attachment.__dict__, "record_revision": expected_revision + 1,
                                     "created_at": str(row[1]), "updated_at": now})
        self.connection.execute(
            "UPDATE p6_gantt_attachment SET project_revision=?,kind=?,label=?,start_date=?,end_date=?,"
            "color=?,activity_id=?,topic_id=?,visible=?,record_revision=?,updated_at=? "
            "WHERE tenant_id=? AND project_id=? AND attachment_id=?",
            (scope.project_revision, updated.kind, updated.label, updated.start_date, updated.end_date,
             updated.color, updated.activity_id, updated.topic_id, 1 if updated.visible else 0,
             updated.record_revision, now, scope.tenant_id, scope.project_id, updated.attachment_id),
        )
        self.connection.commit()
        return updated

    def delete(self, scope: BackendScope, attachment_id: str, expected_revision: int) -> bool:
        scope.validate()
        row = self.connection.execute(
            "SELECT record_revision FROM p6_gantt_attachment "
            "WHERE tenant_id=? AND project_id=? AND attachment_id=?",
            (scope.tenant_id, scope.project_id, attachment_id),
        ).fetchone()
        if row is None:
            raise GanttAttachmentPersistenceError("ATTACHMENT_NOT_FOUND")
        if int(row[0]) != expected_revision:
            raise GanttAttachmentPersistenceError("REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM p6_gantt_attachment WHERE tenant_id=? AND project_id=? AND attachment_id=?",
            (scope.tenant_id, scope.project_id, attachment_id),
        )
        self.connection.commit()
        return True


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> GanttAttachment:
    attachment = GanttAttachment(
        scope=scope,
        attachment_id=str(row[0]),
        kind=str(row[1]),
        label=str(row[2]),
        start_date=None if row[3] is None else str(row[3]),
        end_date=None if row[4] is None else str(row[4]),
        color=None if row[5] is None else str(row[5]),
        activity_id=None if row[6] is None else str(row[6]),
        topic_id=None if row[7] is None else str(row[7]),
        visible=bool(row[8]),
        record_revision=int(row[9]),
        created_at=str(row[10]),
        updated_at=str(row[11]),
    )
    attachment.validate()
    return attachment


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


@dataclass(frozen=True)
class P6GanttAttachmentAPI:
    repository: SQLiteGanttAttachmentRepository
    authorization_policy: AuthorizationPolicy

    def _check(self, scope: BackendScope, auth: AuthorizationContext, permission: Permission) -> None:
        _require_scope(scope, auth)
        if not self.authorization_policy.is_allowed(auth, permission):
            raise AuthorizationError("GANTT_ATTACHMENT_NOT_AUTHORIZED")

    def list(self, scope: BackendScope, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        self._check(scope, auth_context, Permission.PROJECT_READ)
        return {
            "contract_version": GANTT_ATTACHMENT_API_VERSION,
            "kind": "p6_gantt_attachment_list",
            "attachments": [_dto(item) for item in self.repository.list(scope)],
        }

    def create(
        self,
        scope: BackendScope,
        *,
        kind: object,
        label: object,
        start_date: object,
        end_date: object,
        color: object,
        activity_id: object,
        topic_id: object,
        visible: object,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._check(scope, auth_context, Permission.PROJECT_WRITE)
        attachment = GanttAttachment(
            scope=scope,
            attachment_id=f"GATT-{uuid.uuid4()}",
            kind=str(kind or ""),
            label=str(label or "").strip(),
            start_date=_iso_date(start_date, "start_date"),
            end_date=_iso_date(end_date, "end_date"),
            color=None if color in (None, "") else str(color),
            activity_id=None if activity_id in (None, "") else str(activity_id).strip(),
            topic_id=None if topic_id in (None, "") else str(topic_id).strip(),
            visible=True if visible is None else visible,
        )
        stored = self.repository.create(scope, attachment)
        return {"contract_version": GANTT_ATTACHMENT_API_VERSION, "kind": "p6_gantt_attachment", "attachment": _dto(stored)}

    def update(
        self,
        scope: BackendScope,
        attachment_id: str,
        *,
        kind: object,
        label: object,
        start_date: object,
        end_date: object,
        color: object,
        activity_id: object,
        topic_id: object,
        visible: object,
        expected_record_revision: object,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._check(scope, auth_context, Permission.PROJECT_WRITE)
        if isinstance(expected_record_revision, bool) or not isinstance(expected_record_revision, int) or expected_record_revision < 1:
            raise GanttAttachmentPersistenceError("EXPECTED_RECORD_REVISION_REQUIRED")
        attachment = GanttAttachment(
            scope=scope,
            attachment_id=attachment_id,
            kind=str(kind or ""),
            label=str(label or "").strip(),
            start_date=_iso_date(start_date, "start_date"),
            end_date=_iso_date(end_date, "end_date"),
            color=None if color in (None, "") else str(color),
            activity_id=None if activity_id in (None, "") else str(activity_id).strip(),
            topic_id=None if topic_id in (None, "") else str(topic_id).strip(),
            visible=True if visible is None else visible,
        )
        stored = self.repository.update(scope, attachment, expected_record_revision)
        return {"contract_version": GANTT_ATTACHMENT_API_VERSION, "kind": "p6_gantt_attachment", "attachment": _dto(stored)}

    def delete(
        self, scope: BackendScope, attachment_id: str, *, expected_record_revision: object,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        self._check(scope, auth_context, Permission.PROJECT_WRITE)
        if isinstance(expected_record_revision, bool) or not isinstance(expected_record_revision, int) or expected_record_revision < 1:
            raise GanttAttachmentPersistenceError("EXPECTED_RECORD_REVISION_REQUIRED")
        self.repository.delete(scope, attachment_id, expected_record_revision)
        return {
            "contract_version": GANTT_ATTACHMENT_API_VERSION,
            "kind": "p6_gantt_attachment_delete",
            "attachment_id": attachment_id,
            "deleted": True,
        }


def _dto(item: GanttAttachment) -> dict[str, Any]:
    return {
        "attachment_id": item.attachment_id,
        "kind": item.kind,
        "label": item.label,
        "start_date": item.start_date,
        "end_date": item.end_date,
        "color": item.color,
        "activity_id": item.activity_id,
        "topic_id": item.topic_id,
        "visible": item.visible,
        "record_revision": item.record_revision,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


__all__ = [
    "GANTT_ATTACHMENT_API_VERSION",
    "GanttAttachment",
    "GanttAttachmentPersistenceError",
    "P6GanttAttachmentAPI",
    "SQLiteGanttAttachmentRepository",
]
