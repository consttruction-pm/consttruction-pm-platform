"""Project-scoped report definitions and immutable report runs.

A definition selects one authoritative subject and an ordered subset of its
fields. A run materializes that selection from the authoritative dataset at
one project revision and is stored verbatim; a later definition edit never
rewrites an earlier run.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol


class ReportPersistenceError(ValueError):
    """Raised when a report definition or run violates its contract."""


class ReportRevisionConflict(ReportPersistenceError):
    """Raised when a definition write uses a stale record revision."""


class ReportIdempotencyReuse(ReportPersistenceError):
    """Raised when an idempotency key is reused for different content."""


@dataclass(frozen=True)
class ReportField:
    key: str
    label: str
    data_type: str = "string"

    def as_dict(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "data_type": self.data_type}


REPORT_CATALOGUE: dict[str, tuple[ReportField, ...]] = {
    "activities": (
        ReportField("activity_id", "Activity ID"),
        ReportField("name", "Activity Name"),
        ReportField("activity_type", "Activity Type"),
        ReportField("status", "Status"),
        ReportField("actual_start", "Actual Start", "date"),
        ReportField("expected_finish", "Expected Finish", "date"),
        ReportField("duration", "Duration", "decimal"),
        ReportField("percent_complete", "Percent Complete", "decimal"),
    ),
    "resources": (
        ReportField("resource_id", "Resource ID"),
        ReportField("name", "Resource Name"),
        ReportField("resource_type", "Resource Type"),
        ReportField("parent_resource_id", "Parent Resource"),
        ReportField("calendar_id", "Calendar"),
        ReportField("unit_of_measure", "Unit of Measure"),
        ReportField("is_active", "Active", "boolean"),
    ),
    "risks": (
        ReportField("risk_id", "Risk ID"),
        ReportField("title", "Title"),
        ReportField("category", "Category"),
        ReportField("status", "Status"),
        ReportField("probability", "Probability", "integer"),
        ReportField("impact", "Impact", "integer"),
        ReportField("score", "Score", "integer"),
        ReportField("exposure_level", "Exposure"),
    ),
}

SUBJECT_LABELS = {
    "activities": "Activities",
    "resources": "Resources",
    "risks": "Risks",
}


def subject_fields(subject: str) -> tuple[ReportField, ...]:
    fields = REPORT_CATALOGUE.get(subject)
    if fields is None:
        raise ReportPersistenceError("INVALID_REPORT_SUBJECT")
    return fields


def report_catalogue() -> list[dict[str, object]]:
    return [
        {
            "subject": subject,
            "label": SUBJECT_LABELS[subject],
            "fields": [field.as_dict() for field in fields],
        }
        for subject, fields in REPORT_CATALOGUE.items()
    ]


def _required_text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportPersistenceError(code)
    return value


@dataclass(frozen=True)
class ReportDefinition:
    tenant_id: str
    project_id: str
    report_id: str
    name: str
    subject: str
    columns: tuple[str, ...]
    description: str = ""

    def validate(self) -> None:
        for value, code in (
            (self.tenant_id, "INVALID_REPORT_TENANT"),
            (self.project_id, "INVALID_REPORT_PROJECT"),
            (self.report_id, "INVALID_REPORT_ID"),
            (self.name, "INVALID_REPORT_NAME"),
        ):
            _required_text(value, code)
        if not isinstance(self.subject, str) or self.subject not in REPORT_CATALOGUE:
            raise ReportPersistenceError("INVALID_REPORT_SUBJECT")
        if not isinstance(self.description, str):
            raise ReportPersistenceError("INVALID_REPORT_DESCRIPTION")
        if not isinstance(self.columns, tuple) or not self.columns:
            raise ReportPersistenceError("REPORT_COLUMNS_REQUIRED")
        allowed = {field.key for field in REPORT_CATALOGUE[self.subject]}
        seen: set[str] = set()
        for column in self.columns:
            if not isinstance(column, str) or not column.strip():
                raise ReportPersistenceError("INVALID_REPORT_COLUMN")
            if column not in allowed:
                raise ReportPersistenceError("REPORT_COLUMN_NOT_IN_SUBJECT")
            if column in seen:
                raise ReportPersistenceError("REPORT_COLUMN_DUPLICATED")
            seen.add(column)
        if len(seen) != len(self.columns):
            raise ReportPersistenceError("REPORT_COLUMN_DUPLICATED")

    def as_dict(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "name": self.name,
            "description": self.description,
            "subject": self.subject,
            "columns": list(self.columns),
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StoredReportDefinition:
    definition: ReportDefinition
    revision: int

    def as_dict(self) -> dict[str, object]:
        payload = self.definition.as_dict()
        payload["record_revision"] = self.revision
        return payload


@dataclass(frozen=True)
class ReportAuditEvent:
    entity_type: str
    entity_id: str
    revision: int
    event_type: str
    actor_id: str
    occurred_at: datetime
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "revision": self.revision,
            "event_type": self.event_type,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at.isoformat(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ReportRun:
    run_id: str
    tenant_id: str
    project_id: str
    report_id: str
    report_revision: int
    project_revision: int
    subject: str
    columns: tuple[str, ...]
    rows: tuple[Mapping[str, Any], ...]
    generated_at: datetime
    generated_by: str

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "report_id": self.report_id,
            "report_revision": self.report_revision,
            "project_revision": self.project_revision,
            "subject": self.subject,
            "columns": list(self.columns),
            "rows": [dict(row) for row in self.rows],
            "row_count": len(self.rows),
            "generated_at": self.generated_at.isoformat(),
            "generated_by": self.generated_by,
        }


class ReportStore(Protocol):
    def create_definition(
        self,
        definition: ReportDefinition,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredReportDefinition: ...

    def get_definition(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> StoredReportDefinition: ...

    def list_definitions(
        self,
        tenant_id: str,
        project_id: str,
        *,
        subject: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredReportDefinition, ...]: ...

    def update_definition(
        self,
        definition: ReportDefinition,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredReportDefinition: ...

    def delete_definition(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None: ...

    def definition_history(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> tuple[ReportAuditEvent, ...]: ...

    def save_run(self, run: ReportRun) -> ReportRun: ...

    def list_runs(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> tuple[ReportRun, ...]: ...

    def get_run(
        self, tenant_id: str, project_id: str, report_id: str, run_id: str
    ) -> ReportRun: ...

    def next_run_id(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> str: ...


def _validate_actor(actor_id: str) -> None:
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError("INVALID_REPORT_ACTOR")


def _validate_occurred_at(occurred_at: datetime) -> None:
    if not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None:
        raise ValueError("INVALID_REPORT_OCCURRED_AT")


def _fingerprint(definition: ReportDefinition) -> str:
    return definition.fingerprint()


def _definition_from_row(row: tuple[object, ...]) -> StoredReportDefinition:
    definition = ReportDefinition(
        tenant_id=str(row[0]),
        project_id=str(row[1]),
        report_id=str(row[2]),
        name=str(row[3]),
        description=str(row[4]),
        subject=str(row[5]),
        columns=tuple(str(item) for item in json.loads(str(row[6]))),
    )
    definition.validate()
    return StoredReportDefinition(definition=definition, revision=int(row[7]))


def _run_from_row(row: tuple[object, ...]) -> ReportRun:
    return ReportRun(
        run_id=str(row[0]),
        tenant_id=str(row[1]),
        project_id=str(row[2]),
        report_id=str(row[3]),
        report_revision=int(row[4]),
        project_revision=int(row[5]),
        subject=str(row[6]),
        columns=tuple(str(item) for item in json.loads(str(row[7]))),
        rows=tuple(dict(item) for item in json.loads(str(row[8]))),
        generated_at=datetime.fromisoformat(str(row[9])),
        generated_by=str(row[10]),
    )


class SQLiteReportStore:
    """Report definitions, immutable runs and an audit trail in SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_report_definition (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                report_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                subject TEXT NOT NULL,
                columns_json TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, report_id)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_report_audit (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (tenant_id, project_id, entity_type, entity_id, revision)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_report_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                report_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, idempotency_key)
            )"""
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS project_report_run (
                run_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                report_id TEXT NOT NULL,
                report_revision INTEGER NOT NULL,
                project_revision INTEGER NOT NULL,
                subject TEXT NOT NULL,
                columns_json TEXT NOT NULL,
                rows_json TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                generated_by TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, run_id)
            )"""
        )
        self.connection.commit()

    # -- definitions ------------------------------------------------------
    def get_definition(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> StoredReportDefinition:
        row = self.connection.execute(
            """SELECT tenant_id, project_id, report_id, name, description, subject,
                      columns_json, revision
               FROM project_report_definition
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?""",
            (tenant_id, project_id, report_id),
        ).fetchone()
        if row is None:
            raise KeyError("REPORT_NOT_FOUND")
        return _definition_from_row(row)

    def list_definitions(
        self,
        tenant_id: str,
        project_id: str,
        *,
        subject: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredReportDefinition, ...]:
        if subject is not None and subject not in REPORT_CATALOGUE:
            raise ReportPersistenceError("INVALID_REPORT_SUBJECT")
        query = (
            """SELECT tenant_id, project_id, report_id, name, description, subject,
                      columns_json, revision
               FROM project_report_definition
               WHERE tenant_id = ? AND project_id = ?"""
        )
        params: list[object] = [tenant_id, project_id]
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if search:
            query += " AND (report_id LIKE ? OR name LIKE ?)"
            pattern = f"%{search}%"
            params.extend([pattern, pattern])
        query += " ORDER BY report_id"
        return tuple(
            _definition_from_row(row)
            for row in self.connection.execute(query, tuple(params)).fetchall()
        )

    def create_definition(
        self,
        definition: ReportDefinition,
        *,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredReportDefinition:
        definition.validate()
        _validate_actor(actor_id)
        _validate_occurred_at(occurred_at)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ReportPersistenceError("REPORT_IDEMPOTENCY_KEY_REQUIRED")
        fingerprint = _fingerprint(definition)
        existing_key = self.connection.execute(
            """SELECT fingerprint, report_id FROM project_report_idempotency
               WHERE tenant_id = ? AND project_id = ? AND idempotency_key = ?""",
            (definition.tenant_id, definition.project_id, idempotency_key),
        ).fetchone()
        if existing_key is not None:
            if str(existing_key[0]) != fingerprint or str(existing_key[1]) != definition.report_id:
                raise ReportIdempotencyReuse("REPORT_IDEMPOTENCY_KEY_REUSE")
            return self.get_definition(
                definition.tenant_id, definition.project_id, definition.report_id
            )
        existing = self.connection.execute(
            """SELECT 1 FROM project_report_definition
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?""",
            (definition.tenant_id, definition.project_id, definition.report_id),
        ).fetchone()
        if existing is not None:
            raise ReportPersistenceError("REPORT_ID_ALREADY_EXISTS")
        now = occurred_at.isoformat()
        self.connection.execute(
            """INSERT INTO project_report_definition
               (tenant_id, project_id, report_id, name, description, subject,
                columns_json, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (
                definition.tenant_id,
                definition.project_id,
                definition.report_id,
                definition.name,
                definition.description,
                definition.subject,
                json.dumps(list(definition.columns), ensure_ascii=False),
                now,
                now,
            ),
        )
        self.connection.execute(
            """INSERT INTO project_report_idempotency
               (tenant_id, project_id, idempotency_key, fingerprint, report_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                definition.tenant_id,
                definition.project_id,
                idempotency_key,
                fingerprint,
                definition.report_id,
                now,
            ),
        )
        self._audit(
            definition.tenant_id,
            definition.project_id,
            definition.report_id,
            1,
            "created",
            actor_id,
            occurred_at,
            "",
        )
        return StoredReportDefinition(definition=definition, revision=1)

    def update_definition(
        self,
        definition: ReportDefinition,
        *,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> StoredReportDefinition:
        definition.validate()
        _validate_actor(actor_id)
        _validate_occurred_at(occurred_at)
        current = self.get_definition(
            definition.tenant_id, definition.project_id, definition.report_id
        )
        self._check_revision(expected_revision, "INVALID_EXPECTED_REPORT_REVISION")
        if current.revision != expected_revision:
            raise ReportRevisionConflict("REPORT_REVISION_CONFLICT")
        if not isinstance(reason, str):
            raise ReportPersistenceError("INVALID_REPORT_REASON")
        new_revision = current.revision + 1
        now = occurred_at.isoformat()
        self.connection.execute(
            """UPDATE project_report_definition
               SET name = ?, description = ?, subject = ?, columns_json = ?,
                   revision = ?, updated_at = ?
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?""",
            (
                definition.name,
                definition.description,
                definition.subject,
                json.dumps(list(definition.columns), ensure_ascii=False),
                new_revision,
                now,
                definition.tenant_id,
                definition.project_id,
                definition.report_id,
            ),
        )
        self._audit(
            definition.tenant_id,
            definition.project_id,
            definition.report_id,
            new_revision,
            "updated",
            actor_id,
            occurred_at,
            reason,
        )
        return StoredReportDefinition(definition=definition, revision=new_revision)

    def delete_definition(
        self,
        *,
        tenant_id: str,
        project_id: str,
        report_id: str,
        expected_revision: int,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        _validate_actor(actor_id)
        _validate_occurred_at(occurred_at)
        current = self.get_definition(tenant_id, project_id, report_id)
        self._check_revision(expected_revision, "INVALID_EXPECTED_REPORT_REVISION")
        if current.revision != expected_revision:
            raise ReportRevisionConflict("REPORT_REVISION_CONFLICT")
        if not isinstance(reason, str):
            raise ReportPersistenceError("INVALID_REPORT_REASON")
        new_revision = current.revision + 1
        self.connection.execute(
            """DELETE FROM project_report_definition
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?""",
            (tenant_id, project_id, report_id),
        )
        self._audit(
            tenant_id,
            project_id,
            report_id,
            new_revision,
            "deleted",
            actor_id,
            occurred_at,
            reason,
        )

    def definition_history(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> tuple[ReportAuditEvent, ...]:
        rows = self.connection.execute(
            """SELECT entity_type, entity_id, revision, event_type, actor_id,
                      occurred_at, reason
               FROM project_report_audit
               WHERE tenant_id = ? AND project_id = ? AND entity_id = ?
               ORDER BY revision""",
            (tenant_id, project_id, report_id),
        ).fetchall()
        return tuple(
            ReportAuditEvent(
                entity_type=str(row[0]),
                entity_id=str(row[1]),
                revision=int(row[2]),
                event_type=str(row[3]),
                actor_id=str(row[4]),
                occurred_at=datetime.fromisoformat(str(row[5])),
                reason=str(row[6]),
            )
            for row in rows
        )

    # -- runs -------------------------------------------------------------
    def save_run(self, run: ReportRun) -> ReportRun:
        if run.subject not in REPORT_CATALOGUE:
            raise ReportPersistenceError("INVALID_REPORT_SUBJECT")
        if not run.columns or any(column not in {field.key for field in REPORT_CATALOGUE[run.subject]} for column in run.columns):
            raise ReportPersistenceError("INVALID_REPORT_COLUMNS")
        if not isinstance(run.generated_at, datetime) or run.generated_at.tzinfo is None:
            raise ValueError("INVALID_REPORT_GENERATED_AT")
        _validate_actor(run.generated_by)
        if run.report_revision < 1 or run.project_revision < 0:
            raise ReportPersistenceError("INVALID_REPORT_REVISION")
        existing = self.connection.execute(
            """SELECT 1 FROM project_report_run
               WHERE tenant_id = ? AND project_id = ? AND run_id = ?""",
            (run.tenant_id, run.project_id, run.run_id),
        ).fetchone()
        if existing is not None:
            raise ReportPersistenceError("REPORT_RUN_ID_ALREADY_EXISTS")
        self.connection.execute(
            """INSERT INTO project_report_run
               (run_id, tenant_id, project_id, report_id, report_revision,
                project_revision, subject, columns_json, rows_json,
                generated_at, generated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.run_id,
                run.tenant_id,
                run.project_id,
                run.report_id,
                run.report_revision,
                run.project_revision,
                run.subject,
                json.dumps(list(run.columns), ensure_ascii=False),
                json.dumps([dict(row) for row in run.rows], ensure_ascii=False),
                run.generated_at.isoformat(),
                run.generated_by,
            ),
        )
        return run

    def next_run_id(self, tenant_id: str, project_id: str, report_id: str) -> str:
        count = self.connection.execute(
            """SELECT COUNT(*) FROM project_report_run
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?""",
            (tenant_id, project_id, report_id),
        ).fetchone()
        sequence = int(count[0]) + 1 if count is not None else 1
        while True:
            candidate = f"RUN-{report_id}-{sequence}"
            exists = self.connection.execute(
                """SELECT 1 FROM project_report_run
                   WHERE tenant_id = ? AND project_id = ? AND run_id = ?""",
                (tenant_id, project_id, candidate),
            ).fetchone()
            if exists is None:
                return candidate
            sequence += 1

    def list_runs(
        self, tenant_id: str, project_id: str, report_id: str
    ) -> tuple[ReportRun, ...]:
        rows = self.connection.execute(
            """SELECT run_id, tenant_id, project_id, report_id, report_revision,
                      project_revision, subject, columns_json, rows_json,
                      generated_at, generated_by
               FROM project_report_run
               WHERE tenant_id = ? AND project_id = ? AND report_id = ?
               ORDER BY generated_at DESC, run_id DESC""",
            (tenant_id, project_id, report_id),
        ).fetchall()
        return tuple(_run_from_row(row) for row in rows)

    def get_run(
        self, tenant_id: str, project_id: str, report_id: str, run_id: str
    ) -> ReportRun:
        row = self.connection.execute(
            """SELECT run_id, tenant_id, project_id, report_id, report_revision,
                      project_revision, subject, columns_json, rows_json,
                      generated_at, generated_by
               FROM project_report_run
               WHERE tenant_id = ? AND project_id = ? AND report_id = ? AND run_id = ?""",
            (tenant_id, project_id, report_id, run_id),
        ).fetchone()
        if row is None:
            raise KeyError("REPORT_RUN_NOT_FOUND")
        return _run_from_row(row)

    # -- helpers ----------------------------------------------------------
    def _audit(
        self,
        tenant_id: str,
        project_id: str,
        report_id: str,
        revision: int,
        event_type: str,
        actor_id: str,
        occurred_at: datetime,
        reason: str,
    ) -> None:
        self.connection.execute(
            """INSERT INTO project_report_audit
               (tenant_id, project_id, entity_type, entity_id, revision,
                event_type, actor_id, occurred_at, reason)
               VALUES (?, ?, 'report', ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                project_id,
                report_id,
                revision,
                event_type,
                actor_id,
                occurred_at.isoformat(),
                reason,
            ),
        )

    @staticmethod
    def _check_revision(expected_revision: object, code: str) -> None:
        if (
            isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
            or expected_revision < 1
        ):
            raise ReportPersistenceError(code)


__all__ = [
    "REPORT_CATALOGUE",
    "SUBJECT_LABELS",
    "ReportAuditEvent",
    "ReportDefinition",
    "ReportField",
    "ReportIdempotencyReuse",
    "ReportPersistenceError",
    "ReportRevisionConflict",
    "ReportRun",
    "ReportStore",
    "SQLiteReportStore",
    "StoredReportDefinition",
    "report_catalogue",
    "subject_fields",
]
