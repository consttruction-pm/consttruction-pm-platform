from __future__ import annotations

"""Immutable persistence and authoritative replay resolution for CalculationContext."""

import sqlite3
from dataclasses import replace
from typing import Protocol

from .backend_p0.models import BackendScope
from .schedule_input_snapshot_repository import ScheduleInputSnapshot, ScheduleSnapshotPersistenceError
from .scheduling.calculation_context import CalculationContext


class CalculationContextPersistenceError(ValueError):
    """Raised when an authoritative calculation context cannot be persisted or resolved."""


class CalculationContextRepository(Protocol):
    def save(self, context: CalculationContext) -> CalculationContext: ...
    def get(self, scope: BackendScope, snapshot_id: str) -> CalculationContext | None: ...


def _validate_scope(scope: BackendScope, context: CalculationContext) -> None:
    scope.validate()
    if context.input_snapshot_id == "":
        raise CalculationContextPersistenceError("INVALID_INPUT_SNAPSHOT_ID")
    if context.project_id != scope.project_id or context.project_version != scope.project_revision:
        raise CalculationContextPersistenceError("CONTEXT_SCOPE_MISMATCH")
    if context.tenant_id != scope.tenant_id:
        raise CalculationContextPersistenceError("CONTEXT_TENANT_MISMATCH")


def _validate_context(context: CalculationContext) -> None:
    if not isinstance(context, CalculationContext):
        raise CalculationContextPersistenceError("INVALID_CALCULATION_CONTEXT")
    if not context.calculation_identity:
        raise CalculationContextPersistenceError("INVALID_CALCULATION_IDENTITY")


def resolve_authoritative_context(
    snapshot: ScheduleInputSnapshot,
    context: CalculationContext,
) -> CalculationContext:
    """Verify a reconstructed context before it can enter the scheduler."""
    _validate_context(context)
    if context.input_snapshot_id != snapshot.snapshot_id:
        raise CalculationContextPersistenceError("INPUT_SNAPSHOT_ID_MISMATCH")
    if context.project_id != snapshot.scope.project_id:
        raise CalculationContextPersistenceError("PROJECT_ID_MISMATCH")
    if context.project_version != snapshot.scope.project_revision:
        raise CalculationContextPersistenceError("PROJECT_REVISION_MISMATCH")
    if context.tenant_id != snapshot.scope.tenant_id:
        raise CalculationContextPersistenceError("TENANT_ID_MISMATCH")
    if snapshot.calculation_identity_version == 2:
        matches = context.calculation_identity == snapshot.calculation_identity
    elif snapshot.calculation_identity_version == 1:
        matches = context.legacy_calculation_identity == snapshot.calculation_identity
    else:
        raise CalculationContextPersistenceError("INVALID_CALCULATION_IDENTITY_VERSION")
    if not matches:
        raise CalculationContextPersistenceError("CALCULATION_IDENTITY_MISMATCH")
    return context


def resolve_context_for_replay(
    snapshot_repo: object,
    context_repo: CalculationContextRepository,
    scope: BackendScope,
    snapshot_id: str,
) -> tuple[ScheduleInputSnapshot, CalculationContext]:
    """Resolve both immutable inputs and their authoritative persisted context."""
    snapshot = snapshot_repo.get(scope, snapshot_id)
    if snapshot is None:
        raise CalculationContextPersistenceError("SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND")
    context = context_repo.get(scope, snapshot_id)
    if context is None:
        raise CalculationContextPersistenceError("CALCULATION_CONTEXT_NOT_FOUND")
    return snapshot, resolve_authoritative_context(snapshot, context)


class SQLiteCalculationContextRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calculation_context (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                input_snapshot_id TEXT NOT NULL,
                project_version INTEGER NOT NULL,
                calendar_id TEXT NOT NULL,
                calendar_version TEXT NOT NULL,
                rules_version TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                timezone TEXT NOT NULL,
                calculation_timestamp TEXT NOT NULL,
                actor_id TEXT,
                request_id TEXT,
                idempotency_key TEXT,
                calculation_identity TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, input_snapshot_id)
            )"""
        )
        self.connection.commit()

    def save(self, context: CalculationContext) -> CalculationContext:
        _validate_context(context)
        existing = self.get(
            BackendScope(context.tenant_id, context.project_id, context.project_version),
            context.input_snapshot_id,
        )
        if existing is not None:
            if existing.to_dict() == context.to_dict():
                return existing
            raise CalculationContextPersistenceError("CALCULATION_CONTEXT_IMMUTABLE_CONFLICT")
        self.connection.execute(
            """INSERT INTO calculation_context (
                tenant_id, project_id, project_revision, input_snapshot_id,
                project_version, calendar_id, calendar_version, rules_version,
                engine_version, timezone, calculation_timestamp, actor_id,
                request_id, idempotency_key, calculation_identity
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                context.tenant_id, context.project_id, context.project_version,
                context.input_snapshot_id, context.project_version, context.calendar_id,
                context.calendar_version, context.rules_version, context.engine_version,
                context.timezone, context.calculation_timestamp, context.actor_id,
                context.request_id, context.idempotency_key, context.calculation_identity,
            ),
        )
        self.connection.commit()
        return context

    def get(self, scope: BackendScope, snapshot_id: str) -> CalculationContext | None:
        scope.validate()
        row = self.connection.execute(
            """SELECT project_id, project_version, calendar_id, calendar_version,
                      rules_version, engine_version, timezone, calculation_timestamp,
                      input_snapshot_id, tenant_id, actor_id, request_id, idempotency_key
               FROM calculation_context
               WHERE tenant_id=? AND project_id=? AND input_snapshot_id=?""",
            (scope.tenant_id, scope.project_id, snapshot_id),
        ).fetchone()
        if row is None:
            return None
        context = CalculationContext(
            project_id=row[0], project_version=row[1], calendar_id=row[2],
            calendar_version=row[3], rules_version=row[4], engine_version=row[5],
            timezone=row[6], calculation_timestamp=row[7], input_snapshot_id=row[8],
            tenant_id=row[9], actor_id=row[10], request_id=row[11], idempotency_key=row[12],
        )
        if context.project_version != scope.project_revision:
            raise CalculationContextPersistenceError("CONTEXT_REVISION_CONFLICT")
        return context


class PostgresCalculationContextRepository:
    """PostgreSQL adapter for the same immutable context contract."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS calculation_context (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision BIGINT NOT NULL,
                input_snapshot_id TEXT NOT NULL,
                project_version BIGINT NOT NULL,
                calendar_id TEXT NOT NULL,
                calendar_version TEXT NOT NULL,
                rules_version TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                timezone TEXT NOT NULL,
                calculation_timestamp TEXT NOT NULL,
                actor_id TEXT,
                request_id TEXT,
                idempotency_key TEXT,
                calculation_identity TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, input_snapshot_id)
            )"""
        )

    def save(self, context: CalculationContext) -> CalculationContext:
        _validate_context(context)
        inserted = self.connection.execute(
            """INSERT INTO calculation_context (
                tenant_id, project_id, project_revision, input_snapshot_id,
                project_version, calendar_id, calendar_version, rules_version,
                engine_version, timezone, calculation_timestamp, actor_id,
                request_id, idempotency_key, calculation_identity
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (tenant_id, project_id, input_snapshot_id) DO NOTHING
            RETURNING input_snapshot_id""",
            (
                context.tenant_id, context.project_id, context.project_version,
                context.input_snapshot_id, context.project_version, context.calendar_id,
                context.calendar_version, context.rules_version, context.engine_version,
                context.timezone, context.calculation_timestamp, context.actor_id,
                context.request_id, context.idempotency_key, context.calculation_identity,
            ),
        ).fetchone()
        if inserted is not None:
            return context
        scope = BackendScope(context.tenant_id, context.project_id, context.project_version)
        existing = self.get(scope, context.input_snapshot_id)
        if existing is not None and existing.to_dict() == context.to_dict():
            return existing
        raise CalculationContextPersistenceError("CALCULATION_CONTEXT_IMMUTABLE_CONFLICT")

    def get(self, scope: BackendScope, snapshot_id: str) -> CalculationContext | None:
        scope.validate()
        row = self.connection.execute(
            """SELECT project_id, project_version, calendar_id, calendar_version,
                      rules_version, engine_version, timezone, calculation_timestamp,
                      input_snapshot_id, tenant_id, actor_id, request_id, idempotency_key
               FROM calculation_context
               WHERE tenant_id=%s AND project_id=%s AND input_snapshot_id=%s""",
            (scope.tenant_id, scope.project_id, snapshot_id),
        ).fetchone()
        if row is None:
            return None
        context = CalculationContext(
            project_id=row[0], project_version=row[1], calendar_id=row[2],
            calendar_version=row[3], rules_version=row[4], engine_version=row[5],
            timezone=row[6], calculation_timestamp=row[7], input_snapshot_id=row[8],
            tenant_id=row[9], actor_id=row[10], request_id=row[11], idempotency_key=row[12],
        )
        if context.project_version != scope.project_revision:
            raise CalculationContextPersistenceError("CONTEXT_REVISION_CONFLICT")
        return context
