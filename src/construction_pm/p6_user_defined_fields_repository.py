from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .p6_field_registry import P6FieldType


class P6UserDefinedFieldPersistenceError(ValueError):
    """Raised when a persisted P6 custom/UDF definition is invalid or conflicts."""


@dataclass(frozen=True)
class P6UserDefinedFieldDefinition:
    scope: BackendScope
    registry_version: str
    udf_id: str
    subject_area: str
    display_name: str
    data_type: P6FieldType
    writable: bool = True
    nullable: bool = True
    unit: str | None = None
    allowed_values: tuple[str, ...] = ()

    def validate(self) -> None:
        self.scope.validate()
        if self.registry_version != "p6-field-registry.v1":
            raise P6UserDefinedFieldPersistenceError("UNSUPPORTED_REGISTRY_VERSION")
        for value, name in (
            (self.udf_id, "udf_id"),
            (self.subject_area, "subject_area"),
            (self.display_name, "display_name"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6UserDefinedFieldPersistenceError(f"INVALID_{name.upper()}")
        if not isinstance(self.data_type, P6FieldType):
            raise P6UserDefinedFieldPersistenceError("INVALID_DATA_TYPE")
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise P6UserDefinedFieldPersistenceError("INVALID_UNIT")
        if self.data_type is not P6FieldType.ENUM and self.allowed_values:
            raise P6UserDefinedFieldPersistenceError("INVALID_ALLOWED_VALUES")
        if len(self.allowed_values) != len(set(self.allowed_values)):
            raise P6UserDefinedFieldPersistenceError("DUPLICATE_ALLOWED_VALUE")
        if any(not isinstance(value, str) or not value.strip() for value in self.allowed_values):
            raise P6UserDefinedFieldPersistenceError("INVALID_ALLOWED_VALUE")


class P6UserDefinedFieldRepository(Protocol):
    def upsert_definition(
        self, definition: P6UserDefinedFieldDefinition
    ) -> P6UserDefinedFieldDefinition: ...
    def get_definition(
        self, scope: BackendScope, registry_version: str, udf_id: str
    ) -> P6UserDefinedFieldDefinition | None: ...
    def list_definitions(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
    ) -> tuple[P6UserDefinedFieldDefinition, ...]: ...


class SQLiteP6UserDefinedFieldRepository:
    """Tenant/project/revision-scoped persistence for custom P6/UDF definitions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS p6_user_defined_fields (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                registry_version TEXT NOT NULL,
                udf_id TEXT NOT NULL,
                subject_area TEXT NOT NULL,
                display_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                writable INTEGER NOT NULL,
                nullable INTEGER NOT NULL,
                unit TEXT,
                allowed_values_json TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (
                    tenant_id, project_id, registry_version, udf_id
                )
            );
            CREATE INDEX IF NOT EXISTS idx_p6_udf_scope_subject
                ON p6_user_defined_fields (
                    tenant_id, project_id, registry_version, subject_area, udf_id
                );
            """
        )
        self.connection.commit()

    def upsert_definition(
        self, definition: P6UserDefinedFieldDefinition
    ) -> P6UserDefinedFieldDefinition:
        definition.validate()
        payload = json.dumps(
            _definition_payload(definition), sort_keys=True, separators=(",", ":")
        )
        row = self.connection.execute(
            """
            SELECT project_revision, payload_json
            FROM p6_user_defined_fields
            WHERE tenant_id=? AND project_id=? AND registry_version=? AND udf_id=?
            """,
            (
                definition.scope.tenant_id,
                definition.scope.project_id,
                definition.registry_version,
                definition.udf_id,
            ),
        ).fetchone()
        if row is not None:
            if int(row[0]) != definition.scope.project_revision:
                raise P6UserDefinedFieldPersistenceError("REVISION_CONFLICT")
            if row[1] != payload:
                raise P6UserDefinedFieldPersistenceError("IMMUTABLE_UDF_DEFINITION")
            return definition

        self.connection.execute(
            """
            INSERT INTO p6_user_defined_fields (
                tenant_id, project_id, project_revision, registry_version,
                udf_id, subject_area, display_name, data_type, writable,
                nullable, unit, allowed_values_json, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                definition.scope.tenant_id,
                definition.scope.project_id,
                definition.scope.project_revision,
                definition.registry_version,
                definition.udf_id,
                definition.subject_area,
                definition.display_name,
                definition.data_type.value,
                int(definition.writable),
                int(definition.nullable),
                definition.unit,
                json.dumps(list(definition.allowed_values), separators=(",", ":")),
                payload,
            ),
        )
        return definition

    def get_definition(
        self, scope: BackendScope, registry_version: str, udf_id: str
    ) -> P6UserDefinedFieldDefinition | None:
        scope.validate()
        _validate_version_and_id(registry_version, udf_id)
        row = self.connection.execute(
            """
            SELECT project_revision, udf_id, subject_area, display_name,
                   data_type, writable, nullable, unit, allowed_values_json
            FROM p6_user_defined_fields
            WHERE tenant_id=? AND project_id=? AND registry_version=? AND udf_id=?
            """,
            (scope.tenant_id, scope.project_id, registry_version, udf_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6UserDefinedFieldPersistenceError("REVISION_CONFLICT")
        return _definition_from_row(scope, registry_version, row)

    def list_definitions(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
    ) -> tuple[P6UserDefinedFieldDefinition, ...]:
        scope.validate()
        _validate_registry_version(registry_version)
        if subject_area is not None and (
            not isinstance(subject_area, str) or not subject_area.strip()
        ):
            raise P6UserDefinedFieldPersistenceError("INVALID_SUBJECT_AREA")
        query = """
            SELECT project_revision, udf_id, subject_area, display_name,
                   data_type, writable, nullable, unit, allowed_values_json
            FROM p6_user_defined_fields
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
        query += " ORDER BY udf_id"
        rows = self.connection.execute(query, params).fetchall()
        return tuple(_definition_from_row(scope, registry_version, row) for row in rows)


@dataclass(frozen=True)
class P6UserDefinedFieldApplicationService:
    repository: P6UserDefinedFieldRepository
    transaction_manager: object

    def save_definition(
        self, definition: P6UserDefinedFieldDefinition
    ) -> P6UserDefinedFieldDefinition:
        definition.validate()
        with self.transaction_manager.transaction():
            return self.repository.upsert_definition(definition)

    def read_definition(
        self, scope: BackendScope, registry_version: str, udf_id: str
    ) -> P6UserDefinedFieldDefinition | None:
        with self.transaction_manager.transaction():
            return self.repository.get_definition(scope, registry_version, udf_id)

    def list_definitions(
        self,
        scope: BackendScope,
        registry_version: str,
        subject_area: str | None = None,
    ) -> tuple[P6UserDefinedFieldDefinition, ...]:
        with self.transaction_manager.transaction():
            return self.repository.list_definitions(scope, registry_version, subject_area)


def _validate_registry_version(value: str) -> None:
    if value != "p6-field-registry.v1":
        raise P6UserDefinedFieldPersistenceError("UNSUPPORTED_REGISTRY_VERSION")


def _validate_version_and_id(registry_version: str, udf_id: str) -> None:
    _validate_registry_version(registry_version)
    if not isinstance(udf_id, str) or not udf_id.strip():
        raise P6UserDefinedFieldPersistenceError("INVALID_UDF_ID")


def _definition_payload(
    definition: P6UserDefinedFieldDefinition,
) -> dict[str, object]:
    return {
        "scope": {
            "tenant_id": definition.scope.tenant_id,
            "project_id": definition.scope.project_id,
            "project_revision": definition.scope.project_revision,
        },
        "registry_version": definition.registry_version,
        "udf_id": definition.udf_id,
        "subject_area": definition.subject_area,
        "display_name": definition.display_name,
        "data_type": definition.data_type.value,
        "writable": definition.writable,
        "nullable": definition.nullable,
        "unit": definition.unit,
        "allowed_values": list(definition.allowed_values),
    }


def _definition_from_row(
    scope: BackendScope,
    registry_version: str,
    row: tuple[object, ...],
) -> P6UserDefinedFieldDefinition:
    revision, udf_id, subject_area, display_name, data_type, writable, nullable, unit, allowed_values_json = row
    revision = int(revision)
    if revision < 0 or revision > MAX_SAFE_REVISION:
        raise P6UserDefinedFieldPersistenceError("INVALID_PROJECT_REVISION")
    try:
        allowed_values = tuple(json.loads(str(allowed_values_json)))
        definition = P6UserDefinedFieldDefinition(
            scope=scope,
            registry_version=registry_version,
            udf_id=str(udf_id),
            subject_area=str(subject_area),
            display_name=str(display_name),
            data_type=P6FieldType(str(data_type)),
            writable=bool(writable),
            nullable=bool(nullable),
            unit=None if unit is None else str(unit),
            allowed_values=allowed_values,
        )
        definition.validate()
        return definition
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise P6UserDefinedFieldPersistenceError("INVALID_STORED_UDF") from exc


class PostgresP6UserDefinedFieldRepository:
    """Production PostgreSQL adapter for custom/UDF definitions."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_user_defined_fields ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "registry_version TEXT NOT NULL, udf_id TEXT NOT NULL, subject_area TEXT NOT NULL, "
            "display_name TEXT NOT NULL, data_type TEXT NOT NULL, writable BOOLEAN NOT NULL, "
            "nullable BOOLEAN NOT NULL, unit TEXT, allowed_values_json TEXT NOT NULL, payload_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, registry_version, udf_id))"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_p6_udf_scope_subject "
            "ON p6_user_defined_fields (tenant_id, project_id, registry_version, subject_area, udf_id)"
        )

    def upsert_definition(self, definition: P6UserDefinedFieldDefinition) -> P6UserDefinedFieldDefinition:
        definition.validate()
        payload = json.dumps(_definition_payload(definition), sort_keys=True, separators=(",", ":"))
        row = self.connection.execute(
            "SELECT project_revision, payload_json FROM p6_user_defined_fields "
            "WHERE tenant_id=%s AND project_id=%s AND registry_version=%s AND udf_id=%s",
            (definition.scope.tenant_id, definition.scope.project_id, definition.registry_version, definition.udf_id),
        ).fetchone()
        if row is not None:
            if int(row[0]) != definition.scope.project_revision:
                raise P6UserDefinedFieldPersistenceError("REVISION_CONFLICT")
            if row[1] != payload:
                raise P6UserDefinedFieldPersistenceError("IMMUTABLE_UDF_DEFINITION")
            return definition
        self.connection.execute(
            "INSERT INTO p6_user_defined_fields "
            "(tenant_id, project_id, project_revision, registry_version, udf_id, subject_area, display_name, "
            "data_type, writable, nullable, unit, allowed_values_json, payload_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                definition.scope.tenant_id, definition.scope.project_id, definition.scope.project_revision,
                definition.registry_version, definition.udf_id, definition.subject_area,
                definition.display_name, definition.data_type.value, definition.writable, definition.nullable,
                definition.unit, json.dumps(list(definition.allowed_values), separators=(",", ":")), payload,
            ),
        )
        return definition

    def get_definition(self, scope: BackendScope, registry_version: str, udf_id: str) -> P6UserDefinedFieldDefinition | None:
        scope.validate()
        _validate_version_and_id(registry_version, udf_id)
        row = self.connection.execute(
            "SELECT project_revision, udf_id, subject_area, display_name, data_type, writable, nullable, unit, "
            "allowed_values_json FROM p6_user_defined_fields "
            "WHERE tenant_id=%s AND project_id=%s AND registry_version=%s AND udf_id=%s",
            (scope.tenant_id, scope.project_id, registry_version, udf_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6UserDefinedFieldPersistenceError("REVISION_CONFLICT")
        return _definition_from_row(scope, registry_version, row)

    def list_definitions(self, scope: BackendScope, registry_version: str, subject_area: str | None = None) -> tuple[P6UserDefinedFieldDefinition, ...]:
        scope.validate()
        _validate_registry_version(registry_version)
        if subject_area is not None and (not isinstance(subject_area, str) or not subject_area.strip()):
            raise P6UserDefinedFieldPersistenceError("INVALID_SUBJECT_AREA")
        query = (
            "SELECT project_revision, udf_id, subject_area, display_name, data_type, writable, nullable, unit, "
            "allowed_values_json FROM p6_user_defined_fields "
            "WHERE tenant_id=%s AND project_id=%s AND registry_version=%s AND project_revision=%s"
        )
        params: tuple[object, ...] = (scope.tenant_id, scope.project_id, registry_version, scope.project_revision)
        if subject_area is not None:
            query += " AND subject_area=%s"
            params += (subject_area,)
        rows = self.connection.execute(query + " ORDER BY udf_id", params).fetchall()
        return tuple(_definition_from_row(scope, registry_version, row) for row in rows)
