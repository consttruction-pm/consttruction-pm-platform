"""Authoritative project issue register.

Issues are project-scoped records with their own identity and revision. They
are deliberately not bound to the project revision: an issue keeps existing
when activities or WBS elements change. Writes are revision guarded and every
write appends an immutable event row so the register keeps an audit trail.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION

ISSUE_TYPES = frozenset({"cost", "schedule", "quality", "safety", "scope", "resource", "other"})
ISSUE_STATUSES = frozenset({"open", "in_progress", "resolved", "closed"})
ISSUE_PRIORITIES = frozenset({"low", "normal", "high", "critical"})
ISSUE_OPEN_STATUSES = frozenset({"open", "in_progress"})

# Closed issues are final. A resolved issue can be reopened explicitly, which
# keeps the audit trail honest instead of silently editing a closed record.
ISSUE_STATUS_TRANSITIONS = {
    "open": frozenset({"in_progress", "resolved", "closed"}),
    "in_progress": frozenset({"open", "resolved", "closed"}),
    "resolved": frozenset({"open", "closed"}),
    "closed": frozenset(),
}

ISSUE_EVENT_CREATED = "created"
ISSUE_EVENT_UPDATED = "updated"
ISSUE_EVENT_STATUS_CHANGED = "status_changed"
ISSUE_EVENT_COMMENTED = "commented"
ISSUE_EVENT_DELETED = "deleted"


class P6IssuePersistenceError(ValueError):
    """Stable error code for an invalid or conflicting issue write."""


@dataclass(frozen=True)
class P6IssueEvent:
    scope: BackendScope
    issue_id: str
    event_sequence: int
    event_type: str
    actor_id: str
    occurred_at: str
    detail: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "event_sequence": self.event_sequence,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True)
class P6Issue:
    scope: BackendScope
    issue_id: str
    title: str
    description: str
    issue_type: str
    status: str
    priority: str
    owner: str
    responsible_manager: str | None = None
    date_identified: str = ""
    due_date: str | None = None
    wbs_id: str | None = None
    activity_id: str | None = None
    document_refs: tuple[str, ...] = ()
    resolution_note: str | None = None
    record_revision: int = 1
    created_at: str = ""
    updated_at: str = ""

    def validate(self) -> None:
        self.scope.validate()
        for value, code in (
            (self.issue_id, "ISSUE_ID"),
            (self.title, "TITLE"),
            (self.issue_type, "ISSUE_TYPE"),
            (self.status, "STATUS"),
            (self.priority, "PRIORITY"),
            (self.owner, "OWNER"),
            (self.date_identified, "DATE_IDENTIFIED"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6IssuePersistenceError(f"INVALID_{code}")
        if not isinstance(self.description, str):
            raise P6IssuePersistenceError("INVALID_DESCRIPTION")
        if self.issue_type not in ISSUE_TYPES:
            raise P6IssuePersistenceError("INVALID_ISSUE_TYPE")
        if self.status not in ISSUE_STATUSES:
            raise P6IssuePersistenceError("INVALID_STATUS")
        if self.priority not in ISSUE_PRIORITIES:
            raise P6IssuePersistenceError("INVALID_PRIORITY")
        for value, code in (
            (self.responsible_manager, "RESPONSIBLE_MANAGER"),
            (self.wbs_id, "WBS_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.resolution_note, "RESOLUTION_NOTE"),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise P6IssuePersistenceError(f"INVALID_{code}")
        if not isinstance(self.document_refs, tuple):
            raise P6IssuePersistenceError("INVALID_DOCUMENT_REFS")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.document_refs):
            raise P6IssuePersistenceError("INVALID_DOCUMENT_REFS")
        identified = _parse_date(self.date_identified, "INVALID_DATE_IDENTIFIED")
        if self.due_date is not None:
            due = _parse_date(self.due_date, "INVALID_DUE_DATE")
            if due < identified:
                raise P6IssuePersistenceError("ISSUE_DATE_ORDER_INVALID")
        if not isinstance(self.record_revision, int) or isinstance(self.record_revision, bool):
            raise P6IssuePersistenceError("INVALID_RECORD_REVISION")
        if not 1 <= self.record_revision <= MAX_SAFE_REVISION:
            raise P6IssuePersistenceError("INVALID_RECORD_REVISION")
        if self.status in {"resolved", "closed"} and not (self.resolution_note or "").strip():
            raise P6IssuePersistenceError("ISSUE_RESOLUTION_NOTE_REQUIRED")

    def with_revision(self, revision: int) -> "P6Issue":
        return replace(self, record_revision=revision)


def _parse_date(value: str, code: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise P6IssuePersistenceError(code)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise P6IssuePersistenceError(code) from exc


def validate_status_transition(current: str, target: str) -> None:
    if current == target:
        return
    if current not in ISSUE_STATUSES or target not in ISSUE_STATUSES:
        raise P6IssuePersistenceError("INVALID_STATUS")
    if target not in ISSUE_STATUS_TRANSITIONS[current]:
        raise P6IssuePersistenceError("ISSUE_STATUS_TRANSITION_INVALID")


def _document_refs(payload: Any) -> tuple[str, ...]:
    try:
        parsed = json.loads(payload) if isinstance(payload, str) else payload
    except json.JSONDecodeError as exc:
        raise P6IssuePersistenceError("INVALID_STORED_ISSUE") from exc
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise P6IssuePersistenceError("INVALID_STORED_ISSUE")
    return tuple(parsed)


def _from_row(scope: BackendScope, row: tuple[object, ...]) -> P6Issue:
    try:
        result = P6Issue(
            scope=scope,
            issue_id=str(row[0]),
            title=str(row[1]),
            description=str(row[2]),
            issue_type=str(row[3]),
            status=str(row[4]),
            priority=str(row[5]),
            owner=str(row[6]),
            responsible_manager=None if row[7] is None else str(row[7]),
            date_identified=str(row[8]),
            due_date=None if row[9] is None else str(row[9]),
            wbs_id=None if row[10] is None else str(row[10]),
            activity_id=None if row[11] is None else str(row[11]),
            document_refs=_document_refs(row[12]),
            resolution_note=None if row[13] is None else str(row[13]),
            record_revision=int(row[14]),
            created_at=str(row[15]),
            updated_at=str(row[16]),
        )
        result.validate()
        return result
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise P6IssuePersistenceError("INVALID_STORED_ISSUE") from exc


_SELECT = (
    "SELECT issue_id,title,description,issue_type,status,priority,owner,"
    "responsible_manager,date_identified,due_date,wbs_id,activity_id,"
    "document_refs_json,resolution_note,record_revision,created_at,updated_at "
    "FROM p6_issue"
)


class P6IssueRepository(Protocol):
    def create(self, issue: P6Issue, *, actor_id: str, occurred_at: str) -> P6Issue: ...
    def get(self, scope: BackendScope, issue_id: str) -> P6Issue | None: ...
    def list(
        self,
        scope: BackendScope,
        *,
        status: str | None = None,
        priority: str | None = None,
        owner: str | None = None,
        issue_type: str | None = None,
        wbs_id: str | None = None,
        activity_id: str | None = None,
        search: str | None = None,
    ) -> tuple[P6Issue, ...]: ...
    def update(
        self, issue: P6Issue, *, expected_revision: int, actor_id: str, occurred_at: str
    ) -> P6Issue: ...
    def delete(
        self, scope: BackendScope, issue_id: str, *, expected_revision: int,
        actor_id: str, occurred_at: str,
    ) -> bool: ...
    def add_comment(
        self, scope: BackendScope, issue_id: str, *, comment: str,
        expected_revision: int, actor_id: str, occurred_at: str,
    ) -> P6Issue: ...
    def history(self, scope: BackendScope, issue_id: str) -> tuple[P6IssueEvent, ...]: ...


def _validate_filter(name: str, value: str | None, allowed: frozenset[str] | None = None) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise P6IssuePersistenceError(f"INVALID_{name.upper()}_FILTER")
    if allowed is not None and value not in allowed:
        raise P6IssuePersistenceError(f"INVALID_{name.upper()}_FILTER")


def _changed_fields(before: P6Issue, after: P6Issue) -> list[str]:
    names: list[str] = []
    for name in (
        "title", "description", "issue_type", "status", "priority", "owner",
        "responsible_manager", "date_identified", "due_date", "wbs_id",
        "activity_id", "document_refs", "resolution_note",
    ):
        if getattr(before, name) != getattr(after, name):
            names.append(name)
    return names


class SQLiteP6IssueRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_issue ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL, "
            "title TEXT NOT NULL, description TEXT NOT NULL, issue_type TEXT NOT NULL, "
            "status TEXT NOT NULL, priority TEXT NOT NULL, owner TEXT NOT NULL, "
            "responsible_manager TEXT, date_identified TEXT NOT NULL, due_date TEXT, "
            "wbs_id TEXT, activity_id TEXT, document_refs_json TEXT NOT NULL, "
            "resolution_note TEXT, record_revision INTEGER NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, issue_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_issue_scope "
            "ON p6_issue(tenant_id, project_id, status, priority, owner)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_issue_event ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL, "
            "event_sequence INTEGER NOT NULL, event_type TEXT NOT NULL, "
            "actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL, detail_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, issue_id, event_sequence))"
        )
        self.connection.commit()

    def _event(
        self, scope: BackendScope, issue_id: str, event_type: str, actor_id: str,
        occurred_at: str, detail: dict[str, Any],
    ) -> None:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(event_sequence), 0) FROM p6_issue_event "
            "WHERE tenant_id=? AND project_id=? AND issue_id=?",
            (scope.tenant_id, scope.project_id, issue_id),
        ).fetchone()
        sequence = int(row[0]) + 1
        self.connection.execute(
            "INSERT INTO p6_issue_event (tenant_id,project_id,issue_id,event_sequence,"
            "event_type,actor_id,occurred_at,detail_json) VALUES (?,?,?,?,?,?,?,?)",
            (
                scope.tenant_id, scope.project_id, issue_id, sequence, event_type,
                actor_id, occurred_at, json.dumps(detail, sort_keys=True),
            ),
        )

    def create(self, issue: P6Issue, *, actor_id: str, occurred_at: str) -> P6Issue:
        issue.validate()
        if not actor_id.strip() or not occurred_at.strip():
            raise P6IssuePersistenceError("ISSUE_ACTOR_REQUIRED")
        exists = self.connection.execute(
            "SELECT 1 FROM p6_issue WHERE tenant_id=? AND project_id=? AND issue_id=?",
            (issue.scope.tenant_id, issue.scope.project_id, issue.issue_id),
        ).fetchone()
        if exists is not None:
            raise P6IssuePersistenceError("ISSUE_ALREADY_EXISTS")
        stored = replace(issue, record_revision=1, created_at=occurred_at, updated_at=occurred_at)
        self.connection.execute(
            "INSERT INTO p6_issue (tenant_id,project_id,issue_id,title,description,issue_type,"
            "status,priority,owner,responsible_manager,date_identified,due_date,wbs_id,"
            "activity_id,document_refs_json,resolution_note,record_revision,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                stored.scope.tenant_id, stored.scope.project_id, stored.issue_id,
                stored.title, stored.description, stored.issue_type, stored.status,
                stored.priority, stored.owner, stored.responsible_manager,
                stored.date_identified, stored.due_date, stored.wbs_id,
                stored.activity_id, json.dumps(list(stored.document_refs)),
                stored.resolution_note, stored.record_revision, stored.created_at,
                stored.updated_at,
            ),
        )
        self._event(stored.scope, stored.issue_id, ISSUE_EVENT_CREATED, actor_id, occurred_at, {
            "title": stored.title,
            "status": stored.status,
            "priority": stored.priority,
        })
        return stored

    def get(self, scope: BackendScope, issue_id: str) -> P6Issue | None:
        scope.validate()
        if not isinstance(issue_id, str) or not issue_id.strip():
            raise P6IssuePersistenceError("INVALID_ISSUE_ID")
        row = self.connection.execute(
            _SELECT + " WHERE tenant_id=? AND project_id=? AND issue_id=?",
            (scope.tenant_id, scope.project_id, issue_id),
        ).fetchone()
        return None if row is None else _from_row(scope, row)

    def list(
        self,
        scope: BackendScope,
        *,
        status: str | None = None,
        priority: str | None = None,
        owner: str | None = None,
        issue_type: str | None = None,
        wbs_id: str | None = None,
        activity_id: str | None = None,
        search: str | None = None,
    ) -> tuple[P6Issue, ...]:
        scope.validate()
        _validate_filter("status", status, ISSUE_STATUSES)
        _validate_filter("priority", priority, ISSUE_PRIORITIES)
        _validate_filter("issue_type", issue_type, ISSUE_TYPES)
        _validate_filter("owner", owner)
        _validate_filter("wbs_id", wbs_id)
        _validate_filter("activity_id", activity_id)
        _validate_filter("search", search)
        query = _SELECT + " WHERE tenant_id=? AND project_id=?"
        params: list[object] = [scope.tenant_id, scope.project_id]
        for column, value in (
            ("status", status),
            ("priority", priority),
            ("owner", owner),
            ("issue_type", issue_type),
            ("wbs_id", wbs_id),
            ("activity_id", activity_id),
        ):
            if value is not None:
                query += f" AND {column}=?"
                params.append(value)
        if search is not None:
            query += (
                " AND (LOWER(issue_id) LIKE ? OR LOWER(title) LIKE ? "
                "OR LOWER(description) LIKE ? OR LOWER(owner) LIKE ?)"
            )
            needle = f"%{search.lower()}%"
            params.extend([needle, needle, needle, needle])
        query += " ORDER BY issue_id"
        return tuple(_from_row(scope, row) for row in self.connection.execute(query, params).fetchall())

    def update(
        self, issue: P6Issue, *, expected_revision: int, actor_id: str, occurred_at: str
    ) -> P6Issue:
        issue.validate()
        if not isinstance(expected_revision, int) or isinstance(expected_revision, bool):
            raise P6IssuePersistenceError("EXPECTED_REVISION_REQUIRED")
        current = self.get(issue.scope, issue.issue_id)
        if current is None:
            raise P6IssuePersistenceError("ISSUE_NOT_FOUND")
        if current.record_revision != expected_revision:
            raise P6IssuePersistenceError("ISSUE_REVISION_CONFLICT")
        validate_status_transition(current.status, issue.status)
        changed = _changed_fields(current, issue)
        if not changed:
            return current
        stored = replace(
            issue,
            record_revision=current.record_revision + 1,
            created_at=current.created_at,
            updated_at=occurred_at,
        )
        self.connection.execute(
            "UPDATE p6_issue SET title=?,description=?,issue_type=?,status=?,priority=?,"
            "owner=?,responsible_manager=?,date_identified=?,due_date=?,wbs_id=?,"
            "activity_id=?,document_refs_json=?,resolution_note=?,record_revision=?,"
            "updated_at=? WHERE tenant_id=? AND project_id=? AND issue_id=?",
            (
                stored.title, stored.description, stored.issue_type, stored.status,
                stored.priority, stored.owner, stored.responsible_manager,
                stored.date_identified, stored.due_date, stored.wbs_id,
                stored.activity_id, json.dumps(list(stored.document_refs)),
                stored.resolution_note, stored.record_revision, stored.updated_at,
                stored.scope.tenant_id, stored.scope.project_id, stored.issue_id,
            ),
        )
        event_type = (
            ISSUE_EVENT_STATUS_CHANGED if current.status != stored.status else ISSUE_EVENT_UPDATED
        )
        detail: dict[str, Any] = {"fields": changed, "record_revision": stored.record_revision}
        if current.status != stored.status:
            detail.update({"from_status": current.status, "to_status": stored.status})
        self._event(stored.scope, stored.issue_id, event_type, actor_id, occurred_at, detail)
        return stored

    def delete(
        self, scope: BackendScope, issue_id: str, *, expected_revision: int,
        actor_id: str, occurred_at: str,
    ) -> bool:
        scope.validate()
        current = self.get(scope, issue_id)
        if current is None:
            return False
        if current.record_revision != expected_revision:
            raise P6IssuePersistenceError("ISSUE_REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM p6_issue WHERE tenant_id=? AND project_id=? AND issue_id=?",
            (scope.tenant_id, scope.project_id, issue_id),
        )
        self._event(scope, issue_id, ISSUE_EVENT_DELETED, actor_id, occurred_at, {
            "record_revision": current.record_revision,
        })
        return True

    def add_comment(
        self, scope: BackendScope, issue_id: str, *, comment: str,
        expected_revision: int, actor_id: str, occurred_at: str,
    ) -> P6Issue:
        if not isinstance(comment, str) or not comment.strip():
            raise P6IssuePersistenceError("ISSUE_COMMENT_REQUIRED")
        current = self.get(scope, issue_id)
        if current is None:
            raise P6IssuePersistenceError("ISSUE_NOT_FOUND")
        if current.record_revision != expected_revision:
            raise P6IssuePersistenceError("ISSUE_REVISION_CONFLICT")
        stored = replace(
            current,
            record_revision=current.record_revision + 1,
            updated_at=occurred_at,
        )
        self.connection.execute(
            "UPDATE p6_issue SET record_revision=?, updated_at=? "
            "WHERE tenant_id=? AND project_id=? AND issue_id=?",
            (stored.record_revision, stored.updated_at, scope.tenant_id, scope.project_id, issue_id),
        )
        self._event(scope, issue_id, ISSUE_EVENT_COMMENTED, actor_id, occurred_at, {
            "comment": comment.strip(),
            "record_revision": stored.record_revision,
        })
        return stored

    def history(self, scope: BackendScope, issue_id: str) -> tuple[P6IssueEvent, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT event_sequence,event_type,actor_id,occurred_at,detail_json "
            "FROM p6_issue_event WHERE tenant_id=? AND project_id=? AND issue_id=? "
            "ORDER BY event_sequence",
            (scope.tenant_id, scope.project_id, issue_id),
        ).fetchall()
        return tuple(
            P6IssueEvent(
                scope=scope,
                issue_id=issue_id,
                event_sequence=int(row[0]),
                event_type=str(row[1]),
                actor_id=str(row[2]),
                occurred_at=str(row[3]),
                detail=json.loads(str(row[4])),
            )
            for row in rows
        )


class PostgresP6IssueRepository:
    """Postgres mirror of the SQLite issue register (same error contract)."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_issue ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL, "
            "title TEXT NOT NULL, description TEXT NOT NULL, issue_type TEXT NOT NULL, "
            "status TEXT NOT NULL, priority TEXT NOT NULL, owner TEXT NOT NULL, "
            "responsible_manager TEXT, date_identified TEXT NOT NULL, due_date TEXT, "
            "wbs_id TEXT, activity_id TEXT, document_refs_json TEXT NOT NULL, "
            "resolution_note TEXT, record_revision BIGINT NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, issue_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_issue_event ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL, "
            "event_sequence BIGINT NOT NULL, event_type TEXT NOT NULL, "
            "actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL, detail_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, issue_id, event_sequence))"
        )

    def create(self, issue: P6Issue, *, actor_id: str, occurred_at: str) -> P6Issue:
        issue.validate()
        if not actor_id.strip() or not occurred_at.strip():
            raise P6IssuePersistenceError("ISSUE_ACTOR_REQUIRED")
        exists = self.connection.execute(
            "SELECT 1 FROM p6_issue WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
            (issue.scope.tenant_id, issue.scope.project_id, issue.issue_id),
        ).fetchone()
        if exists is not None:
            raise P6IssuePersistenceError("ISSUE_ALREADY_EXISTS")
        stored = replace(issue, record_revision=1, created_at=occurred_at, updated_at=occurred_at)
        self.connection.execute(
            "INSERT INTO p6_issue (tenant_id,project_id,issue_id,title,description,issue_type,"
            "status,priority,owner,responsible_manager,date_identified,due_date,wbs_id,"
            "activity_id,document_refs_json,resolution_note,record_revision,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                stored.scope.tenant_id, stored.scope.project_id, stored.issue_id,
                stored.title, stored.description, stored.issue_type, stored.status,
                stored.priority, stored.owner, stored.responsible_manager,
                stored.date_identified, stored.due_date, stored.wbs_id,
                stored.activity_id, json.dumps(list(stored.document_refs)),
                stored.resolution_note, stored.record_revision, stored.created_at,
                stored.updated_at,
            ),
        )
        self._event(stored, ISSUE_EVENT_CREATED, actor_id, occurred_at, {
            "title": stored.title, "status": stored.status, "priority": stored.priority,
        })
        return stored

    def _event(
        self, issue: P6Issue, event_type: str, actor_id: str, occurred_at: str,
        detail: dict[str, Any],
    ) -> None:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(event_sequence), 0) FROM p6_issue_event "
            "WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
            (issue.scope.tenant_id, issue.scope.project_id, issue.issue_id),
        ).fetchone()
        sequence = int(row[0]) + 1
        self.connection.execute(
            "INSERT INTO p6_issue_event (tenant_id,project_id,issue_id,event_sequence,"
            "event_type,actor_id,occurred_at,detail_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                issue.scope.tenant_id, issue.scope.project_id, issue.issue_id, sequence,
                event_type, actor_id, occurred_at, json.dumps(detail, sort_keys=True),
            ),
        )

    def get(self, scope: BackendScope, issue_id: str) -> P6Issue | None:
        scope.validate()
        if not isinstance(issue_id, str) or not issue_id.strip():
            raise P6IssuePersistenceError("INVALID_ISSUE_ID")
        row = self.connection.execute(
            _SELECT + " WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
            (scope.tenant_id, scope.project_id, issue_id),
        ).fetchone()
        return None if row is None else _from_row(scope, row)

    def list(self, scope: BackendScope, **filters: str | None) -> tuple[P6Issue, ...]:
        scope.validate()
        status = filters.get("status")
        priority = filters.get("priority")
        owner = filters.get("owner")
        issue_type = filters.get("issue_type")
        wbs_id = filters.get("wbs_id")
        activity_id = filters.get("activity_id")
        search = filters.get("search")
        _validate_filter("status", status, ISSUE_STATUSES)
        _validate_filter("priority", priority, ISSUE_PRIORITIES)
        _validate_filter("issue_type", issue_type, ISSUE_TYPES)
        for name, value in (("owner", owner), ("wbs_id", wbs_id), ("activity_id", activity_id), ("search", search)):
            _validate_filter(name, value)
        query = _SELECT + " WHERE tenant_id=%s AND project_id=%s"
        params: list[object] = [scope.tenant_id, scope.project_id]
        for column, value in (
            ("status", status), ("priority", priority), ("owner", owner),
            ("issue_type", issue_type), ("wbs_id", wbs_id), ("activity_id", activity_id),
        ):
            if value is not None:
                query += f" AND {column}=%s"
                params.append(value)
        if search is not None:
            query += (
                " AND (LOWER(issue_id) LIKE %s OR LOWER(title) LIKE %s "
                "OR LOWER(description) LIKE %s OR LOWER(owner) LIKE %s)"
            )
            needle = f"%{search.lower()}%"
            params.extend([needle, needle, needle, needle])
        query += " ORDER BY issue_id"
        return tuple(_from_row(scope, row) for row in self.connection.execute(query, params).fetchall())

    def update(
        self, issue: P6Issue, *, expected_revision: int, actor_id: str, occurred_at: str
    ) -> P6Issue:
        issue.validate()
        if not isinstance(expected_revision, int) or isinstance(expected_revision, bool):
            raise P6IssuePersistenceError("EXPECTED_REVISION_REQUIRED")
        current = self.get(issue.scope, issue.issue_id)
        if current is None:
            raise P6IssuePersistenceError("ISSUE_NOT_FOUND")
        if current.record_revision != expected_revision:
            raise P6IssuePersistenceError("ISSUE_REVISION_CONFLICT")
        validate_status_transition(current.status, issue.status)
        changed = _changed_fields(current, issue)
        if not changed:
            return current
        stored = replace(
            issue, record_revision=current.record_revision + 1,
            created_at=current.created_at, updated_at=occurred_at,
        )
        self.connection.execute(
            "UPDATE p6_issue SET title=%s,description=%s,issue_type=%s,status=%s,priority=%s,"
            "owner=%s,responsible_manager=%s,date_identified=%s,due_date=%s,wbs_id=%s,"
            "activity_id=%s,document_refs_json=%s,resolution_note=%s,record_revision=%s,"
            "updated_at=%s WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
            (
                stored.title, stored.description, stored.issue_type, stored.status,
                stored.priority, stored.owner, stored.responsible_manager,
                stored.date_identified, stored.due_date, stored.wbs_id,
                stored.activity_id, json.dumps(list(stored.document_refs)),
                stored.resolution_note, stored.record_revision, stored.updated_at,
                stored.scope.tenant_id, stored.scope.project_id, stored.issue_id,
            ),
        )
        event_type = (
            ISSUE_EVENT_STATUS_CHANGED if current.status != stored.status else ISSUE_EVENT_UPDATED
        )
        detail: dict[str, Any] = {"fields": changed, "record_revision": stored.record_revision}
        if current.status != stored.status:
            detail.update({"from_status": current.status, "to_status": stored.status})
        self._event(stored, event_type, actor_id, occurred_at, detail)
        return stored

    def delete(
        self, scope: BackendScope, issue_id: str, *, expected_revision: int,
        actor_id: str, occurred_at: str,
    ) -> bool:
        current = self.get(scope, issue_id)
        if current is None:
            return False
        if current.record_revision != expected_revision:
            raise P6IssuePersistenceError("ISSUE_REVISION_CONFLICT")
        self.connection.execute(
            "DELETE FROM p6_issue WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
            (scope.tenant_id, scope.project_id, issue_id),
        )
        self._event(current, ISSUE_EVENT_DELETED, actor_id, occurred_at, {
            "record_revision": current.record_revision,
        })
        return True

    def add_comment(
        self, scope: BackendScope, issue_id: str, *, comment: str,
        expected_revision: int, actor_id: str, occurred_at: str,
    ) -> P6Issue:
        if not isinstance(comment, str) or not comment.strip():
            raise P6IssuePersistenceError("ISSUE_COMMENT_REQUIRED")
        current = self.get(scope, issue_id)
        if current is None:
            raise P6IssuePersistenceError("ISSUE_NOT_FOUND")
        if current.record_revision != expected_revision:
            raise P6IssuePersistenceError("ISSUE_REVISION_CONFLICT")
        stored = replace(current, record_revision=current.record_revision + 1, updated_at=occurred_at)
        self.connection.execute(
            "UPDATE p6_issue SET record_revision=%s, updated_at=%s "
            "WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
            (stored.record_revision, stored.updated_at, scope.tenant_id, scope.project_id, issue_id),
        )
        self._event(stored, ISSUE_EVENT_COMMENTED, actor_id, occurred_at, {
            "comment": comment.strip(), "record_revision": stored.record_revision,
        })
        return stored

    def history(self, scope: BackendScope, issue_id: str) -> tuple[P6IssueEvent, ...]:
        scope.validate()
        rows = self.connection.execute(
            "SELECT event_sequence,event_type,actor_id,occurred_at,detail_json "
            "FROM p6_issue_event WHERE tenant_id=%s AND project_id=%s AND issue_id=%s "
            "ORDER BY event_sequence",
            (scope.tenant_id, scope.project_id, issue_id),
        ).fetchall()
        return tuple(
            P6IssueEvent(
                scope=scope, issue_id=issue_id, event_sequence=int(row[0]),
                event_type=str(row[1]), actor_id=str(row[2]), occurred_at=str(row[3]),
                detail=json.loads(str(row[4])),
            )
            for row in rows
        )


__all__ = [
    "ISSUE_EVENT_COMMENTED",
    "ISSUE_EVENT_CREATED",
    "ISSUE_EVENT_DELETED",
    "ISSUE_EVENT_STATUS_CHANGED",
    "ISSUE_EVENT_UPDATED",
    "ISSUE_OPEN_STATUSES",
    "ISSUE_PRIORITIES",
    "ISSUE_STATUSES",
    "ISSUE_STATUS_TRANSITIONS",
    "ISSUE_TYPES",
    "P6Issue",
    "P6IssueEvent",
    "P6IssuePersistenceError",
    "P6IssueRepository",
    "PostgresP6IssueRepository",
    "SQLiteP6IssueRepository",
    "validate_status_transition",
]
