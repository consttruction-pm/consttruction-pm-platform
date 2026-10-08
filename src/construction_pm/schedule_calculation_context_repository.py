from __future__ import annotations

"""Immutable persistence and replay resolution for authoritative CalculationContext."""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .scheduling.calculation_context import (
    CALCULATION_IDENTITY_VERSION,
    CalculationContext,
)


class CalculationContextPersistenceError(ValueError):
    """Raised for invalid, conflicting, or unverifiable persisted contexts."""


def _parse_revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CalculationContextPersistenceError("INVALID_PROJECT_REVISION")
    if not 0 <= value <= MAX_SAFE_REVISION:
        raise CalculationContextPersistenceError("INVALID_PROJECT_REVISION")
    return value


def _validate_sha(value: object, error_code: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CalculationContextPersistenceError(error_code)
    return value


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CalculationContextPersistenceError(f"INVALID_{field_name.upper()}")
    return value


@dataclass(frozen=True)
class PersistedCalculationContext:
    scope: BackendScope
    snapshot_id: str
    context: CalculationContext
    context_sha256: str
    calculation_identity: str
    calculation_identity_version: str = CALCULATION_IDENTITY_VERSION

    def validate(self) -> None:
        self.scope.validate()
        if not self.snapshot_id.strip():
            raise CalculationContextPersistenceError("INVALID_SNAPSHOT_ID")
        if self.context.input_snapshot_id != self.snapshot_id:
            raise CalculationContextPersistenceError("SNAPSHOT_CONTEXT_ID_MISMATCH")
        if (
            self.context.project_id != self.scope.project_id
            or self.context.project_version != self.scope.project_revision
        ):
            raise CalculationContextPersistenceError("SNAPSHOT_CONTEXT_SCOPE_MISMATCH")
        if self.context.tenant_id is not None and self.context.tenant_id != self.scope.tenant_id:
            raise CalculationContextPersistenceError("SNAPSHOT_CONTEXT_TENANT_MISMATCH")
        _validate_sha(self.context_sha256, "INVALID_CONTEXT_SHA256")
        _validate_sha(self.calculation_identity, "INVALID_CALCULATION_IDENTITY")
        if self.calculation_identity_version != CALCULATION_IDENTITY_VERSION:
            raise CalculationContextPersistenceError("INVALID_CALCULATION_IDENTITY_VERSION")
        if self.context.sha256() != self.context_sha256:
            raise CalculationContextPersistenceError("CONTEXT_SHA256_MISMATCH")
        if self.context.calculation_identity != self.calculation_identity:
            raise CalculationContextPersistenceError("CALCULATION_IDENTITY_MISMATCH")


def build_persisted_context(
    scope: BackendScope,
    context: CalculationContext,
) -> PersistedCalculationContext:
    record = PersistedCalculationContext(
        scope=scope,
        snapshot_id=context.input_snapshot_id,
        context=context,
        context_sha256=context.sha256(),
        calculation_identity=context.calculation_identity,
    )
    record.validate()
    return record


class CalculationContextRepository(Protocol):
    def save(self, record: PersistedCalculationContext) -> PersistedCalculationContext: ...

    def get(
        self,
        scope: BackendScope,
        snapshot_id: str,
        *,
        expected_calculation_identity: str | None = None,
    ) -> PersistedCalculationContext | None: ...


def _reconstruct(
    scope: BackendScope,
    row: tuple[object, ...],
) -> PersistedCalculationContext:
    (
        snapshot_id,
        project_id,
        project_version,
        calendar_id,
        calendar_version,
        rules_version,
        engine_version,
        timezone,
        calculation_timestamp,
        input_snapshot_id,
        tenant_id,
        actor_id,
        request_id,
        idempotency_key,
        context_sha256,
        calculation_identity,
        calculation_identity_version,
    ) = row
    context = CalculationContext(
        project_id=str(project_id),
        project_version=_parse_revision(project_version),
        calendar_id=str(calendar_id),
        calendar_version=str(calendar_version),
        rules_version=str(rules_version),
        engine_version=str(engine_version),
        timezone=str(timezone),
        calculation_timestamp=str(calculation_timestamp),
        input_snapshot_id=str(input_snapshot_id),
        tenant_id=_optional_text(tenant_id, "tenant_id"),
        actor_id=_optional_text(actor_id, "actor_id"),
        request_id=_optional_text(request_id, "request_id"),
        idempotency_key=_optional_text(idempotency_key, "idempotency_key"),
    )
    record = PersistedCalculationContext(
        scope=scope,
        snapshot_id=str(snapshot_id),
        context=context,
        context_sha256=_validate_sha(context_sha256, "INVALID_CONTEXT_SHA256"),
        calculation_identity=_validate_sha(calculation_identity, "INVALID_CALCULATION_IDENTITY"),
        calculation_identity_version=str(calculation_identity_version),
    )
    record.validate()
    return record


class SQLiteCalculationContextRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS schedule_calculation_context (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                snapshot_id TEXT NOT NULL,
                calendar_id TEXT NOT NULL,
                calendar_version TEXT NOT NULL,
                rules_version TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                timezone TEXT NOT NULL,
                calculation_timestamp TEXT NOT NULL,
                input_snapshot_id TEXT NOT NULL,
                tenant_context_id TEXT,
                actor_id TEXT,
                request_id TEXT,
                idempotency_key TEXT,
                context_sha256 TEXT NOT NULL,
                calculation_identity TEXT NOT NULL,
                calculation_identity_version TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, snapshot_id)
            )"""
        )
        self.connection.commit()

    def save(self, record: PersistedCalculationContext) -> PersistedCalculationContext:
        record.validate()
        existing = self.connection.execute(
            "SELECT project_id,project_revision,calendar_id,calendar_version,rules_version,"
            "engine_version,timezone,calculation_timestamp,input_snapshot_id,tenant_context_id,"
            "actor_id,request_id,idempotency_key,context_sha256,calculation_identity,"
            "calculation_identity_version,snapshot_id "
            "FROM schedule_calculation_context "
            "WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (record.scope.tenant_id, record.scope.project_id, record.snapshot_id),
        ).fetchone()
        if existing is not None:
            if (
                existing[0] == record.context.project_id
                and _parse_revision(existing[1]) == record.context.project_version
                and existing[2] == record.context.calendar_id
                and existing[3] == record.context.calendar_version
                and existing[4] == record.context.rules_version
                and existing[5] == record.context.engine_version
                and existing[6] == record.context.timezone
                and existing[7] == record.context.calculation_timestamp
                and existing[8] == record.context.input_snapshot_id
                and existing[9] == record.context.tenant_id
                and existing[10] == record.context.actor_id
                and existing[11] == record.context.request_id
                and existing[12] == record.context.idempotency_key
                and existing[13] == record.context_sha256
                and existing[14] == record.calculation_identity
                and existing[15] == record.calculation_identity_version
            ):
                return record
            raise CalculationContextPersistenceError("CONTEXT_IMMUTABLE_CONFLICT")

        self.connection.execute(
            "INSERT INTO schedule_calculation_context "
            "(tenant_id,project_id,project_revision,snapshot_id,calendar_id,calendar_version,"
            "rules_version,engine_version,timezone,calculation_timestamp,input_snapshot_id,"
            "tenant_context_id,actor_id,request_id,idempotency_key,context_sha256,"
            "calculation_identity,calculation_identity_version) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record.scope.tenant_id,
                record.context.project_id,
                record.context.project_version,
                record.snapshot_id,
                record.context.calendar_id,
                record.context.calendar_version,
                record.context.rules_version,
                record.context.engine_version,
                record.context.timezone,
                record.context.calculation_timestamp,
                record.context.input_snapshot_id,
                record.context.tenant_id,
                record.context.actor_id,
                record.context.request_id,
                record.context.idempotency_key,
                record.context_sha256,
                record.calculation_identity,
                record.calculation_identity_version,
            ),
        )
        self.connection.commit()
        return record

    def get(
        self,
        scope: BackendScope,
        snapshot_id: str,
        *,
        expected_calculation_identity: str | None = None,
    ) -> PersistedCalculationContext | None:
        scope.validate()
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise CalculationContextPersistenceError("INVALID_SNAPSHOT_ID")
        row = self.connection.execute(
            "SELECT snapshot_id,project_id,project_revision,calendar_id,calendar_version,"
            "rules_version,engine_version,timezone,calculation_timestamp,input_snapshot_id,"
            "tenant_context_id,actor_id,request_id,idempotency_key,context_sha256,"
            "calculation_identity,calculation_identity_version "
            "FROM schedule_calculation_context "
            "WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (scope.tenant_id, scope.project_id, snapshot_id),
        ).fetchone()
        if row is None:
            return None
        record = _reconstruct(scope, row)
        if record.context.project_version != scope.project_revision:
            raise CalculationContextPersistenceError("REVISION_CONFLICT")
        if expected_calculation_identity is not None:
            _validate_sha(expected_calculation_identity, "INVALID_CALCULATION_IDENTITY")
            if record.calculation_identity != expected_calculation_identity:
                raise CalculationContextPersistenceError("CALCULATION_IDENTITY_MISMATCH")
        return record


class PostgresCalculationContextRepository:
    """PostgreSQL adapter for immutable authoritative CalculationContext records."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS schedule_calculation_context (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision BIGINT NOT NULL,
                snapshot_id TEXT NOT NULL,
                calendar_id TEXT NOT NULL,
                calendar_version TEXT NOT NULL,
                rules_version TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                timezone TEXT NOT NULL,
                calculation_timestamp TEXT NOT NULL,
                input_snapshot_id TEXT NOT NULL,
                tenant_context_id TEXT,
                actor_id TEXT,
                request_id TEXT,
                idempotency_key TEXT,
                context_sha256 TEXT NOT NULL,
                calculation_identity TEXT NOT NULL,
                calculation_identity_version TEXT NOT NULL,
                PRIMARY KEY (tenant_id, project_id, snapshot_id)
            )"""
        )

    def save(self, record: PersistedCalculationContext) -> PersistedCalculationContext:
        record.validate()
        existing = self.connection.execute(
            "SELECT project_id,project_revision,calendar_id,calendar_version,rules_version,"
            "engine_version,timezone,calculation_timestamp,input_snapshot_id,tenant_context_id,"
            "actor_id,request_id,idempotency_key,context_sha256,calculation_identity,"
            "calculation_identity_version "
            "FROM schedule_calculation_context "
            "WHERE tenant_id=%s AND project_id=%s AND snapshot_id=%s",
            (record.scope.tenant_id, record.scope.project_id, record.snapshot_id),
        ).fetchone()
        if existing is not None:
            if (
                existing[0] == record.context.project_id
                and _parse_revision(existing[1]) == record.context.project_version
                and existing[2] == record.context.calendar_id
                and existing[3] == record.context.calendar_version
                and existing[4] == record.context.rules_version
                and existing[5] == record.context.engine_version
                and existing[6] == record.context.timezone
                and existing[7] == record.context.calculation_timestamp
                and existing[8] == record.context.input_snapshot_id
                and existing[9] == record.context.tenant_id
                and existing[10] == record.context.actor_id
                and existing[11] == record.context.request_id
                and existing[12] == record.context.idempotency_key
                and existing[13] == record.context_sha256
                and existing[14] == record.calculation_identity
                and existing[15] == record.calculation_identity_version
            ):
                return record
            raise CalculationContextPersistenceError("CONTEXT_IMMUTABLE_CONFLICT")

        self.connection.execute(
            "INSERT INTO schedule_calculation_context "
            "(tenant_id,project_id,project_revision,snapshot_id,calendar_id,calendar_version,"
            "rules_version,engine_version,timezone,calculation_timestamp,input_snapshot_id,"
            "tenant_context_id,actor_id,request_id,idempotency_key,context_sha256,"
            "calculation_identity,calculation_identity_version) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                record.scope.tenant_id,
                record.context.project_id,
                record.context.project_version,
                record.snapshot_id,
                record.context.calendar_id,
                record.context.calendar_version,
                record.context.rules_version,
                record.context.engine_version,
                record.context.timezone,
                record.context.calculation_timestamp,
                record.context.input_snapshot_id,
                record.context.tenant_id,
                record.context.actor_id,
                record.context.request_id,
                record.context.idempotency_key,
                record.context_sha256,
                record.calculation_identity,
                record.calculation_identity_version,
            ),
        )
        return record

    def get(
        self,
        scope: BackendScope,
        snapshot_id: str,
        *,
        expected_calculation_identity: str | None = None,
    ) -> PersistedCalculationContext | None:
        scope.validate()
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise CalculationContextPersistenceError("INVALID_SNAPSHOT_ID")
        row = self.connection.execute(
            "SELECT snapshot_id,project_id,project_revision,calendar_id,calendar_version,"
            "rules_version,engine_version,timezone,calculation_timestamp,input_snapshot_id,"
            "tenant_context_id,actor_id,request_id,idempotency_key,context_sha256,"
            "calculation_identity,calculation_identity_version "
            "FROM schedule_calculation_context "
            "WHERE tenant_id=%s AND project_id=%s AND snapshot_id=%s",
            (scope.tenant_id, scope.project_id, snapshot_id),
        ).fetchone()
        if row is None:
            return None
        record = _reconstruct(scope, row)
        if record.context.project_version != scope.project_revision:
            raise CalculationContextPersistenceError("REVISION_CONFLICT")
        if expected_calculation_identity is not None:
            _validate_sha(expected_calculation_identity, "INVALID_CALCULATION_IDENTITY")
            if record.calculation_identity != expected_calculation_identity:
                raise CalculationContextPersistenceError("CALCULATION_IDENTITY_MISMATCH")
        return record


__all__ = [
    "CalculationContextPersistenceError",
    "CalculationContextRepository",
    "PersistedCalculationContext",
    "SQLiteCalculationContextRepository",
    "PostgresCalculationContextRepository",
    "build_persisted_context",
]
