from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .p6_field_registry import P6FieldDefinition, P6FieldType


class P6FieldRegistryPersistenceError(ValueError):
    """Raised when persisted P6 field-registry state is invalid or conflicting."""


@dataclass(frozen=True)
class PersistedP6Field:
    scope: BackendScope
    registry_version: str
    field: P6FieldDefinition

    def validate(self) -> None:
        self.scope.validate()
        if self.registry_version != "p6-field-registry.v1":
            raise P6FieldRegistryPersistenceError("UNSUPPORTED_REGISTRY_VERSION")
        self.field.__post_init__()


class P6FieldRegistryRepository(Protocol):
    def upsert_field(self, record: PersistedP6Field) -> PersistedP6Field: ...
    def get_field(
        self,
        scope: BackendScope,
        registry_version: str,
        field_id: str,
    ) -> PersistedP6Field | None: ...
    def list_fields(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
    ) -> tuple[PersistedP6Field, ...]: ...


class SQLiteP6FieldRegistryRepository:
    """Tenant/project/revision-scoped persistence for shared P6 field metadata."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS p6_field_registry (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                registry_version TEXT NOT NULL,
                field_id TEXT NOT NULL,
                subject_area TEXT NOT NULL,
                p6_field TEXT NOT NULL,
                display_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                writable INTEGER NOT NULL,
                computed INTEGER NOT NULL,
                unit TEXT,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (
                    tenant_id, project_id, registry_version, field_id
                )
            );
            CREATE INDEX IF NOT EXISTS idx_p6_field_registry_scope_subject
                ON p6_field_registry (
                    tenant_id, project_id, registry_version, subject_area, field_id
                );
            """
        )
        self.connection.commit()

    def upsert_field(self, record: PersistedP6Field) -> PersistedP6Field:
        record.validate()
        payload = json.dumps(_record_payload(record), sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            """
            SELECT project_revision, payload_json
            FROM p6_field_registry
            WHERE tenant_id=? AND project_id=? AND registry_version=? AND field_id=?
            """,
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.registry_version,
                record.field.field_id,
            ),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6FieldRegistryPersistenceError("REVISION_CONFLICT")
            if row[1] != payload:
                raise P6FieldRegistryPersistenceError("IMMUTABLE_FIELD_DEFINITION")
            return record

        self.connection.execute(
            """
            INSERT INTO p6_field_registry (
                tenant_id, project_id, project_revision, registry_version,
                field_id, subject_area, p6_field, display_name, data_type,
                writable, computed, unit, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.scope.tenant_id,
                record.scope.project_id,
                record.scope.project_revision,
                record.registry_version,
                record.field.field_id,
                record.field.subject_area,
                record.field.p6_field,
                record.field.display_name,
                record.field.data_type.value,
                int(record.field.writable),
                int(record.field.computed),
                record.field.unit,
                payload,
            ),
        )
        return record

    def get_field(
        self,
        scope: BackendScope,
        registry_version: str,
        field_id: str,
    ) -> PersistedP6Field | None:
        scope.validate()
        _validate_version_and_field_id(registry_version, field_id)
        row = self.connection.execute(
            """
            SELECT project_revision, field_id, subject_area, p6_field,
                   display_name, data_type, writable, computed, unit
            FROM p6_field_registry
            WHERE tenant_id=? AND project_id=? AND registry_version=? AND field_id=?
            """,
            (
                scope.tenant_id,
                scope.project_id,
                registry_version,
                field_id,
            ),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6FieldRegistryPersistenceError("REVISION_CONFLICT")
        return _record_from_row(scope, registry_version, row)

    def list_fields(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
    ) -> tuple[PersistedP6Field, ...]:
        scope.validate()
        _validate_registry_version(registry_version)
        if subject_area is not None and (
            not isinstance(subject_area, str) or not subject_area.strip()
        ):
            raise P6FieldRegistryPersistenceError("INVALID_SUBJECT_AREA")

        query = """
            SELECT project_revision, field_id, subject_area, p6_field,
                   display_name, data_type, writable, computed, unit
            FROM p6_field_registry
            WHERE tenant_id=? AND project_id=? AND registry_version=? AND project_revision=?
        """
        params: tuple[object, ...] = (
            scope.tenant_id,
            scope.project_id,
            registry_version,
            scope.project_revision,
        )
        if subject_area is not None:
            query += " AND subject_area=?"
            params += (subject_area,)
        query += " ORDER BY field_id"
        rows = self.connection.execute(query, params).fetchall()
        return tuple(_record_from_row(scope, registry_version, row) for row in rows)


@dataclass(frozen=True)
class P6FieldRegistryApplicationService:
    repository: P6FieldRegistryRepository
    transaction_manager: object

    def save_field(self, record: PersistedP6Field) -> PersistedP6Field:
        record.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert_field(record)

    def read_field(
        self,
        scope: BackendScope,
        registry_version: str,
        field_id: str,
    ) -> PersistedP6Field | None:
        with self.transaction_manager.transaction():
            return self.repository.get_field(scope, registry_version, field_id)

    def list_fields(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
    ) -> tuple[PersistedP6Field, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list_fields(scope, registry_version, subject_area)


def _validate_registry_version(value: str) -> None:
    if value != "p6-field-registry.v1":
        raise P6FieldRegistryPersistenceError("UNSUPPORTED_REGISTRY_VERSION")


def _validate_version_and_field_id(registry_version: str, field_id: str) -> None:
    _validate_registry_version(registry_version)
    if not isinstance(field_id, str) or not field_id.strip():
        raise P6FieldRegistryPersistenceError("INVALID_FIELD_ID")


def _record_payload(record: PersistedP6Field) -> dict[str, object]:
    return {
        "scope": {
            "tenant_id": record.scope.tenant_id,
            "project_id": record.scope.project_id,
            "project_revision": record.scope.project_revision,
        },
        "registry_version": record.registry_version,
        "field": {
            "field_id": record.field.field_id,
            "subject_area": record.field.subject_area,
            "p6_field": record.field.p6_field,
            "display_name": record.field.display_name,
            "data_type": record.field.data_type.value,
            "writable": record.field.writable,
            "computed": record.field.computed,
            "unit": record.field.unit,
        },
    }


def _record_from_row(
    scope: BackendScope,
    registry_version: str,
    row: tuple[object, ...],
) -> PersistedP6Field:
    project_revision, field_id, subject_area, p6_field, display_name, data_type, writable, computed, unit = row
    revision = int(project_revision)
    if revision < 0 or revision > MAX_SAFE_REVISION:
        raise P6FieldRegistryPersistenceError("INVALID_PROJECT_REVISION")
    try:
        field = P6FieldDefinition(
            field_id=str(field_id),
            subject_area=str(subject_area),
            p6_field=str(p6_field),
            display_name=str(display_name),
            data_type=P6FieldType(str(data_type)),
            writable=bool(writable),
            computed=bool(computed),
            unit=None if unit is None else str(unit),
        )
    except (TypeError, ValueError) as exc:
        raise P6FieldRegistryPersistenceError("INVALID_STORED_FIELD") from exc
    record = PersistedP6Field(scope=scope, registry_version=registry_version, field=field)
    record.validate()
    return record


class PostgresP6FieldRegistryRepository:
    """Production PostgreSQL adapter for the authoritative P6 field registry."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_field_registry ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "registry_version TEXT NOT NULL, field_id TEXT NOT NULL, subject_area TEXT NOT NULL, "
            "p6_field TEXT NOT NULL, display_name TEXT NOT NULL, data_type TEXT NOT NULL, "
            "writable BOOLEAN NOT NULL, computed BOOLEAN NOT NULL, unit TEXT, payload_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, registry_version, field_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_field_registry_scope_subject "
            "ON p6_field_registry (tenant_id, project_id, registry_version, subject_area, field_id)"
        )

    def upsert_field(self, record: PersistedP6Field) -> PersistedP6Field:
        record.validate()
        payload = json.dumps(_record_payload(record), sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            "SELECT project_revision, payload_json FROM p6_field_registry "
            "WHERE tenant_id=%s AND project_id=%s AND registry_version=%s AND field_id=%s",
            (record.scope.tenant_id, record.scope.project_id, record.registry_version, record.field.field_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != record.scope.project_revision:
                raise P6FieldRegistryPersistenceError("REVISION_CONFLICT")
            if row[1] != payload:
                raise P6FieldRegistryPersistenceError("IMMUTABLE_FIELD_DEFINITION")
            return record
        self.connection.execute(
            "INSERT INTO p6_field_registry "
            "(tenant_id, project_id, project_revision, registry_version, field_id, subject_area, "
            "p6_field, display_name, data_type, writable, computed, unit, payload_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                record.scope.tenant_id, record.scope.project_id, record.scope.project_revision,
                record.registry_version, record.field.field_id, record.field.subject_area,
                record.field.p6_field, record.field.display_name, record.field.data_type.value,
                record.field.writable, record.field.computed, record.field.unit, payload,
            ),
        )
        return record

    def get_field(self, scope: BackendScope, registry_version: str, field_id: str) -> PersistedP6Field | None:
        scope.validate()
        _validate_version_and_field_id(registry_version, field_id)
        row = self.connection.execute(
            "SELECT project_revision, field_id, subject_area, p6_field, display_name, data_type, "
            "writable, computed, unit FROM p6_field_registry "
            "WHERE tenant_id=%s AND project_id=%s AND registry_version=%s AND field_id=%s",
            (scope.tenant_id, scope.project_id, registry_version, field_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6FieldRegistryPersistenceError("REVISION_CONFLICT")
        return _record_from_row(scope, registry_version, row)

    def list_fields(self, scope: BackendScope, registry_version: str, subject_area: str | None = None) -> tuple[PersistedP6Field, ...]:
        scope.validate()
        _validate_registry_version(registry_version)
        if subject_area is not None and (not isinstance(subject_area, str) or not subject_area.strip()):
            raise P6FieldRegistryPersistenceError("INVALID_SUBJECT_AREA")
        query = (
            "SELECT project_revision, field_id, subject_area, p6_field, display_name, data_type, "
            "writable, computed, unit FROM p6_field_registry "
            "WHERE tenant_id=%s AND project_id=%s AND registry_version=%s AND project_revision=%s"
        )
        params: tuple[object, ...] = (
            scope.tenant_id, scope.project_id, registry_version, scope.project_revision
        )
        if subject_area is not None:
            query += " AND subject_area=%s"
            params += (subject_area,)
        rows = self.connection.execute(query + " ORDER BY field_id", params).fetchall()
        return tuple(_record_from_row(scope, registry_version, row) for row in rows)
