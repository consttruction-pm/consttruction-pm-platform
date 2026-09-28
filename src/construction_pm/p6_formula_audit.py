from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class P6FormulaAuditError(ValueError):
    """Raised when formula audit state is invalid or conflicting."""


@dataclass(frozen=True)
class P6FormulaAuditEvent:
    event_id: str
    scope: BackendScope
    formula_id: str
    formula_version: str
    action: str
    actor_id: str
    occurred_at: datetime
    semantic_version: str
    expression_sha256: str

    def validate(self) -> None:
        self.scope.validate()
        for name, value in (
            ("event_id", self.event_id),
            ("formula_id", self.formula_id),
            ("formula_version", self.formula_version),
            ("actor_id", self.actor_id),
            ("semantic_version", self.semantic_version),
            ("expression_sha256", self.expression_sha256),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6FormulaAuditError(f"INVALID_{name.upper()}")
        if self.action not in {"create"}:
            raise P6FormulaAuditError("INVALID_ACTION")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise P6FormulaAuditError("INVALID_OCCURRED_AT")
        if len(self.expression_sha256) != 64:
            raise P6FormulaAuditError("INVALID_EXPRESSION_SHA256")


class P6FormulaAuditRepository(Protocol):
    def record(self, event: P6FormulaAuditEvent) -> P6FormulaAuditEvent: ...

    def list_events(
        self,
        scope: BackendScope,
        formula_id: str,
    ) -> tuple[P6FormulaAuditEvent, ...]: ...


def expression_sha256(expression: str) -> str:
    if not isinstance(expression, str) or not expression:
        raise P6FormulaAuditError("INVALID_EXPRESSION")
    return hashlib.sha256(expression.encode("utf-8")).hexdigest()


def new_create_event(
    *,
    scope: BackendScope,
    formula_id: str,
    formula_version: str,
    actor_id: str,
    occurred_at: datetime,
    semantic_version: str,
    expression: str,
) -> P6FormulaAuditEvent:
    event = P6FormulaAuditEvent(
        event_id=str(uuid.uuid4()),
        scope=scope,
        formula_id=formula_id,
        formula_version=formula_version,
        action="create",
        actor_id=actor_id,
        occurred_at=occurred_at,
        semantic_version=semantic_version,
        expression_sha256=expression_sha256(expression),
    )
    event.validate()
    return event


class SQLiteP6FormulaAuditRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS p6_formula_audit_events (
                event_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                formula_id TEXT NOT NULL,
                formula_version TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                semantic_version TEXT NOT NULL,
                expression_sha256 TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_p6_formula_audit_scope
                ON p6_formula_audit_events
                (tenant_id, project_id, formula_id, occurred_at, event_id)
            """
        )
        self.connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_p6_formula_audit_version_action
                ON p6_formula_audit_events
                (tenant_id, project_id, formula_id, formula_version, action)
            """
        )
        self.connection.commit()

    def record(self, event: P6FormulaAuditEvent) -> P6FormulaAuditEvent:
        event.validate()
        self.connection.execute(
            """
            INSERT OR IGNORE INTO p6_formula_audit_events (
                event_id, tenant_id, project_id, project_revision,
                formula_id, formula_version, action, actor_id, occurred_at,
                semantic_version, expression_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.scope.tenant_id,
                event.scope.project_id,
                event.scope.project_revision,
                event.formula_id,
                event.formula_version,
                event.action,
                event.actor_id,
                event.occurred_at.isoformat(),
                event.semantic_version,
                event.expression_sha256,
            ),
        )
        return event

    def list_events(
        self,
        scope: BackendScope,
        formula_id: str,
    ) -> tuple[P6FormulaAuditEvent, ...]:
        scope.validate()
        if not isinstance(formula_id, str) or not formula_id.strip():
            raise P6FormulaAuditError("INVALID_FORMULA_ID")
        rows = self.connection.execute(
            """
            SELECT event_id, project_revision, formula_id, formula_version,
                   action, actor_id, occurred_at, semantic_version,
                   expression_sha256
            FROM p6_formula_audit_events
            WHERE tenant_id=? AND project_id=? AND project_revision=? AND formula_id=?
            ORDER BY occurred_at, event_id
            """,
            (
                scope.tenant_id,
                scope.project_id,
                scope.project_revision,
                formula_id,
            ),
        ).fetchall()
        return tuple(_event_from_row(scope, row) for row in rows)


class PostgresP6FormulaAuditRepository:
    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_formula_audit_events ("
            "event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, formula_id TEXT NOT NULL, formula_version TEXT NOT NULL, "
            "action TEXT NOT NULL, actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL, "
            "semantic_version TEXT NOT NULL, expression_sha256 TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_formula_audit_scope "
            "ON p6_formula_audit_events "
            "(tenant_id, project_id, formula_id, occurred_at, event_id)"
        )
        self.connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_p6_formula_audit_version_action "
            "ON p6_formula_audit_events "
            "(tenant_id, project_id, formula_id, formula_version, action)"
        )

    def record(self, event: P6FormulaAuditEvent) -> P6FormulaAuditEvent:
        event.validate()
        self.connection.execute(
            "INSERT INTO p6_formula_audit_events "
            "(event_id, tenant_id, project_id, project_revision, formula_id, formula_version, "
            "action, actor_id, occurred_at, semantic_version, expression_sha256) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, project_id, formula_id, formula_version, action) DO NOTHING",
            (
                event.event_id,
                event.scope.tenant_id,
                event.scope.project_id,
                event.scope.project_revision,
                event.formula_id,
                event.formula_version,
                event.action,
                event.actor_id,
                event.occurred_at.isoformat(),
                event.semantic_version,
                event.expression_sha256,
            ),
        )
        return event

    def list_events(
        self,
        scope: BackendScope,
        formula_id: str,
    ) -> tuple[P6FormulaAuditEvent, ...]:
        scope.validate()
        if not isinstance(formula_id, str) or not formula_id.strip():
            raise P6FormulaAuditError("INVALID_FORMULA_ID")
        rows = self.connection.execute(
            "SELECT event_id, project_revision, formula_id, formula_version, action, actor_id, "
            "occurred_at, semantic_version, expression_sha256 "
            "FROM p6_formula_audit_events "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s AND formula_id=%s "
            "ORDER BY occurred_at, event_id",
            (
                scope.tenant_id,
                scope.project_id,
                scope.project_revision,
                formula_id,
            ),
        ).fetchall()
        return tuple(_event_from_row(scope, row) for row in rows)


def _event_from_row(
    scope: BackendScope,
    row: tuple[object, ...],
) -> P6FormulaAuditEvent:
    (
        event_id,
        project_revision,
        formula_id,
        formula_version,
        action,
        actor_id,
        occurred_at,
        semantic_version,
        expression_sha256_value,
    ) = row
    if int(project_revision) < 0 or int(project_revision) > MAX_SAFE_REVISION:
        raise P6FormulaAuditError("INVALID_PROJECT_REVISION")
    try:
        parsed_at = datetime.fromisoformat(str(occurred_at))
    except ValueError as exc:
        raise P6FormulaAuditError("INVALID_STORED_OCCURRED_AT") from exc
    event = P6FormulaAuditEvent(
        event_id=str(event_id),
        scope=scope,
        formula_id=str(formula_id),
        formula_version=str(formula_version),
        action=str(action),
        actor_id=str(actor_id),
        occurred_at=parsed_at,
        semantic_version=str(semantic_version),
        expression_sha256=str(expression_sha256_value),
    )
    event.validate()
    return event


__all__ = [
    "P6FormulaAuditError",
    "P6FormulaAuditEvent",
    "P6FormulaAuditRepository",
    "PostgresP6FormulaAuditRepository",
    "SQLiteP6FormulaAuditRepository",
    "expression_sha256",
    "new_create_event",
]
