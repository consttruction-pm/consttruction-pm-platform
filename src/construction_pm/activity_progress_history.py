from __future__ import annotations

"""Append-only progress update history for Activity Master records.

The Activity Master row keeps the current progress state. This module records
each progress-bearing change as an immutable event so the Progress window can
show what changed, who changed it, and whether the update was out of sequence
against the stored relationship network. Events are never updated or deleted.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from .activity_master_repository import ActivityMaster
from .backend_p0.models import BackendScope
from .relationship_master_repository import RelationshipMaster
from .scheduling.relationships import RelationshipType


# Fields surfaced by the Progress window. Revisions still increment for any
# activity edit, but only a change in one of these fields is a progress event.
PROGRESS_TRACKED_FIELDS: tuple[str, ...] = (
    "actual_start",
    "actual_finish",
    "percent_complete",
    "remaining_duration",
    "remaining_start",
    "expected_finish",
    "status",
    "status_code",
)


class ProgressHistoryPersistenceError(ValueError):
    """Raised when a progress history event is invalid or unreadable."""


def _iso(value: date | datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def progress_field_value(activity: ActivityMaster, field: str) -> str | None:
    """Normalise one tracked progress field to its stored textual form."""
    if field == "actual_start":
        return _iso(activity.actual_start)
    if field == "actual_finish":
        return _iso(activity.actual_finish)
    if field == "remaining_start":
        return _iso(activity.remaining_start)
    if field == "expected_finish":
        return _iso(activity.expected_finish)
    if field == "percent_complete":
        return None if activity.percent_complete is None else str(activity.percent_complete)
    if field == "remaining_duration":
        return None if activity.remaining_duration is None else str(activity.remaining_duration)
    if field == "status":
        return activity.status.value
    if field == "status_code":
        return activity.status_code.value
    raise ProgressHistoryPersistenceError("UNKNOWN_PROGRESS_FIELD")


@dataclass(frozen=True)
class ProgressFieldChange:
    field: str
    before: str | None
    after: str | None

    def validate(self) -> None:
        if self.field not in PROGRESS_TRACKED_FIELDS:
            raise ProgressHistoryPersistenceError("UNKNOWN_PROGRESS_FIELD")
        if self.before == self.after:
            raise ProgressHistoryPersistenceError("EMPTY_PROGRESS_CHANGE")

    def as_json(self) -> dict[str, object]:
        return {"field": self.field, "before": self.before, "after": self.after}


@dataclass(frozen=True)
class ProgressOutOfSequenceFinding:
    """One stored relationship that the recorded progress contradicts."""

    code: str
    relationship_id: str
    predecessor_id: str
    relationship_type: str

    def validate(self) -> None:
        for name, value in (
            ("code", self.code),
            ("relationship_id", self.relationship_id),
            ("predecessor_id", self.predecessor_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProgressHistoryPersistenceError(f"INVALID_PROGRESS_FINDING_{name.upper()}")
        try:
            RelationshipType(self.relationship_type)
        except ValueError as exc:
            raise ProgressHistoryPersistenceError("INVALID_PROGRESS_FINDING_TYPE") from exc

    def as_json(self) -> dict[str, object]:
        return {
            "code": self.code,
            "relationship_id": self.relationship_id,
            "predecessor_id": self.predecessor_id,
            "relationship_type": self.relationship_type,
        }


@dataclass(frozen=True)
class ActivityProgressEvent:
    scope: BackendScope
    event_id: str
    activity_id: str
    recorded_at: datetime
    actor_user_id: str
    from_record_revision: int
    to_record_revision: int
    changes: tuple[ProgressFieldChange, ...] = ()
    findings: tuple[ProgressOutOfSequenceFinding, ...] = ()

    def validate(self) -> None:
        self.scope.validate()
        for name, value in (
            ("event_id", self.event_id),
            ("activity_id", self.activity_id),
            ("actor_user_id", self.actor_user_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProgressHistoryPersistenceError(f"INVALID_PROGRESS_EVENT_{name.upper()}")
        if not isinstance(self.recorded_at, datetime) or self.recorded_at.tzinfo is None:
            raise ProgressHistoryPersistenceError("INVALID_PROGRESS_EVENT_RECORDED_AT")
        for name, value in (
            ("from_record_revision", self.from_record_revision),
            ("to_record_revision", self.to_record_revision),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ProgressHistoryPersistenceError(f"INVALID_PROGRESS_EVENT_{name.upper()}")
        if self.to_record_revision <= self.from_record_revision:
            raise ProgressHistoryPersistenceError("INVALID_PROGRESS_EVENT_REVISION_SPAN")
        for change in self.changes:
            change.validate()
        for finding in self.findings:
            finding.validate()

    @property
    def out_of_sequence(self) -> bool:
        return bool(self.findings)


def diff_progress_fields(
    previous: ActivityMaster, current: ActivityMaster
) -> tuple[ProgressFieldChange, ...]:
    changes: list[ProgressFieldChange] = []
    for field in PROGRESS_TRACKED_FIELDS:
        before = progress_field_value(previous, field)
        after = progress_field_value(current, field)
        if before != after:
            changes.append(ProgressFieldChange(field, before, after))
    return tuple(changes)


def _as_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def evaluate_out_of_sequence(
    activity: ActivityMaster,
    relationships: tuple[RelationshipMaster, ...],
    activities: tuple[ActivityMaster, ...],
) -> tuple[ProgressOutOfSequenceFinding, ...]:
    """Review recorded actual dates against the stored predecessor logic.

    Only finish-to-start, start-to-start and finish-to-finish links are reviewed
    with the actual dates that the activity master stores. There is no float or
    calendar calculation here; the review is a deterministic comparison of
    persisted facts, and it is captured with the event it was evaluated against.
    """
    by_id = {item.activity_id: item for item in activities}
    findings: list[ProgressOutOfSequenceFinding] = []
    for relationship in relationships:
        if relationship.successor_id != activity.activity_id:
            continue
        predecessor = by_id.get(relationship.predecessor_id)
        if predecessor is None:
            continue
        code: str | None = None
        if relationship.relationship_type is RelationshipType.FS:
            successor_start = _as_date(activity.actual_start)
            predecessor_finish = _as_date(predecessor.actual_finish)
            if successor_start is not None:
                if predecessor_finish is None:
                    code = "FS_PREDECESSOR_NOT_FINISHED"
                elif successor_start < predecessor_finish:
                    code = "FS_START_BEFORE_PREDECESSOR_FINISH"
        elif relationship.relationship_type is RelationshipType.SS:
            successor_start = _as_date(activity.actual_start)
            predecessor_start = _as_date(predecessor.actual_start)
            if (
                successor_start is not None
                and predecessor_start is not None
                and successor_start < predecessor_start
            ):
                code = "SS_START_BEFORE_PREDECESSOR_START"
        elif relationship.relationship_type is RelationshipType.FF:
            successor_finish = _as_date(activity.actual_finish)
            predecessor_finish = _as_date(predecessor.actual_finish)
            if (
                successor_finish is not None
                and predecessor_finish is not None
                and successor_finish < predecessor_finish
            ):
                code = "FF_FINISH_BEFORE_PREDECESSOR_FINISH"
        if code is not None:
            findings.append(
                ProgressOutOfSequenceFinding(
                    code=code,
                    relationship_id=relationship.relationship_id,
                    predecessor_id=predecessor.activity_id,
                    relationship_type=relationship.relationship_type.value,
                )
            )
    findings.sort(key=lambda item: (item.relationship_id, item.code))
    return tuple(findings)


class ActivityProgressHistoryRepository(Protocol):
    def append(self, event: ActivityProgressEvent) -> ActivityProgressEvent: ...
    def list(
        self, scope: BackendScope, activity_id: str
    ) -> tuple[ActivityProgressEvent, ...]: ...
    def latest(
        self, scope: BackendScope, activity_id: str
    ) -> ActivityProgressEvent | None: ...


def _event_from_row(scope: BackendScope, row: tuple[object, ...]) -> ActivityProgressEvent:
    try:
        changes_raw = json.loads(str(row[6]))
        findings_raw = json.loads(str(row[7]))
        if not isinstance(changes_raw, list) or not isinstance(findings_raw, list):
            raise ValueError("INVALID_HISTORY_JSON")
        if not all(isinstance(item, dict) for item in changes_raw):
            raise ValueError("INVALID_HISTORY_JSON")
        if not all(isinstance(item, dict) for item in findings_raw):
            raise ValueError("INVALID_HISTORY_JSON")
        event = ActivityProgressEvent(
            scope=scope,
            event_id=str(row[0]),
            activity_id=str(row[1]),
            recorded_at=datetime.fromisoformat(str(row[2])),
            actor_user_id=str(row[3]),
            from_record_revision=int(row[4]),
            to_record_revision=int(row[5]),
            changes=tuple(
                ProgressFieldChange(
                    field=str(item["field"]),
                    before=None if item.get("before") is None else str(item["before"]),
                    after=None if item.get("after") is None else str(item["after"]),
                )
                for item in changes_raw
            ),
            findings=tuple(
                ProgressOutOfSequenceFinding(
                    code=str(item["code"]),
                    relationship_id=str(item["relationship_id"]),
                    predecessor_id=str(item["predecessor_id"]),
                    relationship_type=str(item["relationship_type"]),
                )
                for item in findings_raw
            ),
        )
        event.validate()
        return event
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise ProgressHistoryPersistenceError("INVALID_STORED_PROGRESS_EVENT") from exc


def _event_payload(event: ActivityProgressEvent) -> tuple[object, ...]:
    return (
        event.scope.tenant_id,
        event.scope.project_id,
        event.event_id,
        event.activity_id,
        event.recorded_at.isoformat(),
        event.actor_user_id,
        event.from_record_revision,
        event.to_record_revision,
        json.dumps([item.as_json() for item in event.changes], separators=(",", ":")),
        json.dumps([item.as_json() for item in event.findings], separators=(",", ":")),
    )


_SQLITE_SELECT = (
    "event_id,activity_id,recorded_at,actor_user_id,from_record_revision,"
    "to_record_revision,changes_json,findings_json"
)


class SQLiteActivityProgressHistoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        was_in_transaction = self.connection.in_transaction
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS activity_progress_event (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                from_record_revision INTEGER NOT NULL,
                to_record_revision INTEGER NOT NULL,
                changes_json TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, event_id)
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_progress_event_activity "
            "ON activity_progress_event(tenant_id, project_id, activity_id, to_record_revision)"
        )
        if not was_in_transaction:
            self.connection.commit()

    def append(self, event: ActivityProgressEvent) -> ActivityProgressEvent:
        event.validate()
        was_in_transaction = self.connection.in_transaction
        if not was_in_transaction:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.connection.execute(
                "INSERT INTO activity_progress_event (tenant_id,project_id,event_id,"
                "activity_id,recorded_at,actor_user_id,from_record_revision,"
                "to_record_revision,changes_json,findings_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(tenant_id,project_id,event_id) DO NOTHING",
                _event_payload(event),
            )
            row = self.connection.execute(
                f"SELECT {_SQLITE_SELECT} FROM activity_progress_event "
                "WHERE tenant_id=? AND project_id=? AND event_id=?",
                (event.scope.tenant_id, event.scope.project_id, event.event_id),
            ).fetchone()
            if row is None:
                raise ProgressHistoryPersistenceError("PROGRESS_EVENT_NOT_STORED")
            if not was_in_transaction:
                self.connection.commit()
            return _event_from_row(event.scope, row)
        except Exception:
            if not was_in_transaction and self.connection.in_transaction:
                self.connection.rollback()
            raise

    def list(
        self, scope: BackendScope, activity_id: str
    ) -> tuple[ActivityProgressEvent, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {_SQLITE_SELECT} FROM activity_progress_event "
            "WHERE tenant_id=? AND project_id=? AND activity_id=? "
            "ORDER BY to_record_revision ASC, recorded_at ASC, event_id ASC",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchall()
        return tuple(_event_from_row(scope, row) for row in rows)

    def latest(
        self, scope: BackendScope, activity_id: str
    ) -> ActivityProgressEvent | None:
        events = self.list(scope, activity_id)
        return events[-1] if events else None


class PostgresActivityProgressHistoryRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS activity_progress_event ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, event_id TEXT NOT NULL, "
            "activity_id TEXT NOT NULL, recorded_at TEXT NOT NULL, actor_user_id TEXT NOT NULL, "
            "from_record_revision BIGINT NOT NULL, to_record_revision BIGINT NOT NULL, "
            "changes_json TEXT NOT NULL, findings_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, event_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_activity_progress_event_activity "
            "ON activity_progress_event(tenant_id, project_id, activity_id, to_record_revision)"
        )

    def append(self, event: ActivityProgressEvent) -> ActivityProgressEvent:
        event.validate()
        self.connection.execute(
            "INSERT INTO activity_progress_event (tenant_id,project_id,event_id,"
            "activity_id,recorded_at,actor_user_id,from_record_revision,"
            "to_record_revision,changes_json,findings_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (tenant_id,project_id,event_id) DO NOTHING",
            _event_payload(event),
        )
        row = self.connection.execute(
            f"SELECT {_SQLITE_SELECT} FROM activity_progress_event "
            "WHERE tenant_id=%s AND project_id=%s AND event_id=%s",
            (event.scope.tenant_id, event.scope.project_id, event.event_id),
        ).fetchone()
        if row is None:
            raise ProgressHistoryPersistenceError("PROGRESS_EVENT_NOT_STORED")
        return _event_from_row(event.scope, row)

    def list(
        self, scope: BackendScope, activity_id: str
    ) -> tuple[ActivityProgressEvent, ...]:
        scope.validate()
        rows = self.connection.execute(
            f"SELECT {_SQLITE_SELECT} FROM activity_progress_event "
            "WHERE tenant_id=%s AND project_id=%s AND activity_id=%s "
            "ORDER BY to_record_revision ASC, recorded_at ASC, event_id ASC",
            (scope.tenant_id, scope.project_id, activity_id),
        ).fetchall()
        return tuple(_event_from_row(scope, row) for row in rows)

    def latest(
        self, scope: BackendScope, activity_id: str
    ) -> ActivityProgressEvent | None:
        events = self.list(scope, activity_id)
        return events[-1] if events else None


__all__ = [
    "PROGRESS_TRACKED_FIELDS",
    "ActivityProgressEvent",
    "ActivityProgressHistoryRepository",
    "PostgresActivityProgressHistoryRepository",
    "ProgressFieldChange",
    "ProgressHistoryPersistenceError",
    "ProgressOutOfSequenceFinding",
    "SQLiteActivityProgressHistoryRepository",
    "diff_progress_fields",
    "evaluate_out_of_sequence",
    "progress_field_value",
]
