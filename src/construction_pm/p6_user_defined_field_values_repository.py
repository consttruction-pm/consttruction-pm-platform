from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION
from .p6_field_registry import P6FieldType
from .p6_user_defined_fields_repository import (
    P6UserDefinedFieldDefinition,
    P6UserDefinedFieldPersistenceError,
    P6UserDefinedFieldRepository,
)


class P6UserDefinedFieldValuePersistenceError(ValueError):
    """Raised when a typed P6 custom/UDF value is invalid or conflicts."""


@dataclass(frozen=True)
class P6DurationValue:
    value: Decimal
    unit: str

    def validate(self) -> None:
        if not isinstance(self.value, Decimal):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DURATION_VALUE")
        if not self.value.is_finite():
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DURATION_VALUE")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DURATION_UNIT")


@dataclass(frozen=True)
class P6UserDefinedFieldValue:
    scope: BackendScope
    udf_id: str
    object_type: str
    object_id: str
    value: object

    def validate_against(self, definition: P6UserDefinedFieldDefinition) -> None:
        self.scope.validate()
        if definition.scope != self.scope:
            raise P6UserDefinedFieldValuePersistenceError("REVISION_CONFLICT")
        for value, name in (
            (self.udf_id, "udf_id"),
            (self.object_type, "object_type"),
            (self.object_id, "object_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise P6UserDefinedFieldValuePersistenceError(f"INVALID_{name.upper()}")

        kind = definition.data_type
        if kind is P6FieldType.DATE:
            if not isinstance(self.value, date) or isinstance(self.value, datetime):
                raise P6UserDefinedFieldValuePersistenceError("INVALID_DATE_VALUE")
        elif kind is P6FieldType.DATETIME:
            if (
                not isinstance(self.value, datetime)
                or self.value.tzinfo is None
                or self.value.utcoffset() is None
            ):
                raise P6UserDefinedFieldValuePersistenceError("INVALID_DATETIME_VALUE")
        elif kind in {P6FieldType.DECIMAL, P6FieldType.DOUBLE, P6FieldType.COST, P6FieldType.PERCENTAGE}:
            if not isinstance(self.value, Decimal) or not self.value.is_finite():
                raise P6UserDefinedFieldValuePersistenceError("INVALID_DECIMAL_VALUE")
        elif kind is P6FieldType.INTEGER:
            if not isinstance(self.value, int) or isinstance(self.value, bool):
                raise P6UserDefinedFieldValuePersistenceError("INVALID_INTEGER_VALUE")
        elif kind is P6FieldType.BOOLEAN:
            if not isinstance(self.value, bool):
                raise P6UserDefinedFieldValuePersistenceError("INVALID_BOOLEAN_VALUE")
        elif kind is P6FieldType.ENUM:
            if not isinstance(self.value, str) or self.value not in definition.allowed_values:
                raise P6UserDefinedFieldValuePersistenceError("INVALID_ENUM_VALUE")
        elif kind is P6FieldType.DURATION:
            if not isinstance(self.value, P6DurationValue):
                raise P6UserDefinedFieldValuePersistenceError("INVALID_DURATION_VALUE")
            self.value.validate()
        else:
            raise P6UserDefinedFieldValuePersistenceError("UNSUPPORTED_TYPED_UDF_VALUE")


class P6UserDefinedFieldValueRepository(Protocol):
    def upsert_value(
        self,
        value: P6UserDefinedFieldValue,
        definition: P6UserDefinedFieldDefinition,
    ) -> P6UserDefinedFieldValue: ...
    def get_value(
        self,
        scope: BackendScope,
        udf_id: str,
        object_type: str,
        object_id: str,
        definition: P6UserDefinedFieldDefinition,
    ) -> P6UserDefinedFieldValue | None: ...


class SQLiteP6UserDefinedFieldValueRepository:
    """Revision-scoped typed UDF value persistence; calculation stays in Shared Core."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS p6_user_defined_field_values (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision INTEGER NOT NULL,
                udf_id TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                value_type TEXT NOT NULL,
                value_json TEXT NOT NULL,
                PRIMARY KEY (
                    tenant_id, project_id, project_revision,
                    udf_id, object_type, object_id
                )
            );
            """
        )
        self.connection.commit()

    def upsert_value(
        self,
        value: P6UserDefinedFieldValue,
        definition: P6UserDefinedFieldDefinition,
    ) -> P6UserDefinedFieldValue:
        value.validate_against(definition)
        value_type, encoded = _encode_value(definition.data_type, value.value)
        row = self.connection.execute(
            """
            SELECT value_type, value_json
            FROM p6_user_defined_field_values
            WHERE tenant_id=? AND project_id=? AND project_revision=?
              AND udf_id=? AND object_type=? AND object_id=?
            """,
            (
                value.scope.tenant_id,
                value.scope.project_id,
                value.scope.project_revision,
                value.udf_id,
                value.object_type,
                value.object_id,
            ),
        ).fetchone()
        if row is None:
            self.connection.execute(
                """
                INSERT INTO p6_user_defined_field_values (
                    tenant_id, project_id, project_revision, udf_id,
                    object_type, object_id, value_type, value_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    value.scope.tenant_id,
                    value.scope.project_id,
                    value.scope.project_revision,
                    value.udf_id,
                    value.object_type,
                    value.object_id,
                    value_type,
                    encoded,
                ),
            )
        else:
            self.connection.execute(
                """
                UPDATE p6_user_defined_field_values
                SET value_type=?, value_json=?
                WHERE tenant_id=? AND project_id=? AND project_revision=?
                  AND udf_id=? AND object_type=? AND object_id=?
                """,
                (
                    value_type,
                    encoded,
                    value.scope.tenant_id,
                    value.scope.project_id,
                    value.scope.project_revision,
                    value.udf_id,
                    value.object_type,
                    value.object_id,
                ),
            )
        return value

    def get_value(
        self,
        scope: BackendScope,
        udf_id: str,
        object_type: str,
        object_id: str,
        definition: P6UserDefinedFieldDefinition,
    ) -> P6UserDefinedFieldValue | None:
        scope.validate()
        definition.validate()
        if definition.scope != scope or definition.udf_id != udf_id:
            raise P6UserDefinedFieldValuePersistenceError("REVISION_CONFLICT")
        for item, name in ((udf_id, "udf_id"), (object_type, "object_type"), (object_id, "object_id")):
            if not isinstance(item, str) or not item.strip():
                raise P6UserDefinedFieldValuePersistenceError(f"INVALID_{name.upper()}")
        row = self.connection.execute(
            """
            SELECT project_revision, value_type, value_json
            FROM p6_user_defined_field_values
            WHERE tenant_id=? AND project_id=? AND project_revision=?
              AND udf_id=? AND object_type=? AND object_id=?
            """,
            (
                scope.tenant_id,
                scope.project_id,
                scope.project_revision,
                udf_id,
                object_type,
                object_id,
            ),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6UserDefinedFieldValuePersistenceError("REVISION_CONFLICT")
        decoded = _decode_value(definition.data_type, str(row[2]), str(row[1]))
        result = P6UserDefinedFieldValue(
            scope=scope,
            udf_id=udf_id,
            object_type=object_type,
            object_id=object_id,
            value=decoded,
        )
        result.validate_against(definition)
        return result


@dataclass(frozen=True)
class P6UserDefinedFieldValueApplicationService:
    repository: P6UserDefinedFieldValueRepository
    definition_repository: P6UserDefinedFieldRepository
    transaction_manager: object

    def save_value(self, value: P6UserDefinedFieldValue) -> P6UserDefinedFieldValue:
        try:
            definition = self.definition_repository.get_definition(
                value.scope, "p6-field-registry.v1", value.udf_id
            )
        except P6UserDefinedFieldPersistenceError as exc:
            raise P6UserDefinedFieldValuePersistenceError(str(exc)) from exc
        if definition is None:
            raise P6UserDefinedFieldValuePersistenceError("UDF_NOT_FOUND")
        with self.transaction_manager.transaction():
            return self.repository.upsert_value(value, definition)

    def read_value(
        self,
        scope: BackendScope,
        udf_id: str,
        object_type: str,
        object_id: str,
    ) -> P6UserDefinedFieldValue | None:
        try:
            definition = self.definition_repository.get_definition(
                scope, "p6-field-registry.v1", udf_id
            )
        except P6UserDefinedFieldPersistenceError as exc:
            raise P6UserDefinedFieldValuePersistenceError(str(exc)) from exc
        if definition is None:
            raise P6UserDefinedFieldValuePersistenceError("UDF_NOT_FOUND")
        with self.transaction_manager.transaction():
            return self.repository.get_value(
                scope, udf_id, object_type, object_id, definition
            )


def _encode_value(data_type: P6FieldType, value: object) -> tuple[str, str]:
    if data_type is P6FieldType.DATE:
        return "date", json.dumps(value.isoformat())
    if data_type is P6FieldType.DATETIME:
        return "datetime", json.dumps(value.isoformat())
    if data_type in {P6FieldType.DECIMAL, P6FieldType.DOUBLE, P6FieldType.COST, P6FieldType.PERCENTAGE}:
        return "decimal", json.dumps(str(value))
    if data_type is P6FieldType.INTEGER:
        return "integer", json.dumps(value)
    if data_type is P6FieldType.BOOLEAN:
        return "boolean", json.dumps(value)
    if data_type is P6FieldType.ENUM:
        return "enum", json.dumps(value)
    if data_type is P6FieldType.DURATION:
        duration = value
        return "duration", json.dumps({"value": str(duration.value), "unit": duration.unit}, sort_keys=True)
    raise P6UserDefinedFieldValuePersistenceError("UNSUPPORTED_TYPED_UDF_VALUE")


def _decode_value(data_type: P6FieldType, payload: str, stored_type: str) -> object:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise P6UserDefinedFieldValuePersistenceError("INVALID_STORED_UDF_VALUE") from exc
    expected = {
        P6FieldType.DATE: "date",
        P6FieldType.DATETIME: "datetime",
        P6FieldType.DECIMAL: "decimal",
        P6FieldType.DOUBLE: "decimal",
        P6FieldType.COST: "decimal",
        P6FieldType.PERCENTAGE: "decimal",
        P6FieldType.INTEGER: "integer",
        P6FieldType.BOOLEAN: "boolean",
        P6FieldType.ENUM: "enum",
        P6FieldType.DURATION: "duration",
    }.get(data_type)
    if expected != stored_type:
        raise P6UserDefinedFieldValuePersistenceError("STORED_VALUE_TYPE_MISMATCH")
    try:
        if data_type is P6FieldType.DATE:
            return date.fromisoformat(str(raw))
        if data_type is P6FieldType.DATETIME:
            result = datetime.fromisoformat(str(raw))
            if result.tzinfo is None or result.utcoffset() is None:
                raise ValueError("timezone required")
            return result
        if data_type in {P6FieldType.DECIMAL, P6FieldType.DOUBLE, P6FieldType.COST, P6FieldType.PERCENTAGE}:
            return Decimal(str(raw))
        if data_type is P6FieldType.INTEGER:
            if isinstance(raw, bool):
                raise ValueError("boolean is not integer")
            return int(raw)
        if data_type is P6FieldType.BOOLEAN:
            if not isinstance(raw, bool):
                raise ValueError("boolean required")
            return raw
        if data_type is P6FieldType.ENUM:
            return str(raw)
        if data_type is P6FieldType.DURATION:
            return P6DurationValue(Decimal(str(raw["value"])), str(raw["unit"]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise P6UserDefinedFieldValuePersistenceError("INVALID_STORED_UDF_VALUE") from exc
    raise P6UserDefinedFieldValuePersistenceError("UNSUPPORTED_TYPED_UDF_VALUE")


__all__ = [
    "P6DurationValue",
    "P6UserDefinedFieldValue",
    "P6UserDefinedFieldValueApplicationService",
    "P6UserDefinedFieldValuePersistenceError",
    "SQLiteP6UserDefinedFieldValueRepository",
]


class PostgresP6UserDefinedFieldValueRepository:
    """Production PostgreSQL adapter for revision-scoped typed UDF values."""

    def __init__(self, connection: object) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS p6_user_defined_field_values ("
            "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "udf_id TEXT NOT NULL, object_type TEXT NOT NULL, object_id TEXT NOT NULL, "
            "value_type TEXT NOT NULL, value_json TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, project_revision, udf_id, object_type, object_id))"
        )

    def upsert_value(self, value: P6UserDefinedFieldValue, definition: P6UserDefinedFieldDefinition) -> P6UserDefinedFieldValue:
        value.validate_against(definition)
        value_type, encoded = _encode_value(definition.data_type, value.value)
        self.connection.execute(
            "INSERT INTO p6_user_defined_field_values "
            "(tenant_id, project_id, project_revision, udf_id, object_type, object_id, value_type, value_json) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (tenant_id, project_id, project_revision, udf_id, object_type, object_id) "
            "DO UPDATE SET value_type=EXCLUDED.value_type, value_json=EXCLUDED.value_json",
            (
                value.scope.tenant_id, value.scope.project_id, value.scope.project_revision,
                value.udf_id, value.object_type, value.object_id, value_type, encoded,
            ),
        )
        return value

    def get_value(
        self, scope: BackendScope, udf_id: str, object_type: str, object_id: str,
        definition: P6UserDefinedFieldDefinition,
    ) -> P6UserDefinedFieldValue | None:
        scope.validate()
        definition.validate()
        if definition.scope != scope or definition.udf_id != udf_id:
            raise P6UserDefinedFieldValuePersistenceError("REVISION_CONFLICT")
        for item, name in ((udf_id, "udf_id"), (object_type, "object_type"), (object_id, "object_id")):
            if not isinstance(item, str) or not item.strip():
                raise P6UserDefinedFieldValuePersistenceError(f"INVALID_{name.upper()}")
        row = self.connection.execute(
            "SELECT project_revision, value_type, value_json FROM p6_user_defined_field_values "
            "WHERE tenant_id=%s AND project_id=%s AND project_revision=%s "
            "AND udf_id=%s AND object_type=%s AND object_id=%s",
            (scope.tenant_id, scope.project_id, scope.project_revision, udf_id, object_type, object_id),
        ).fetchone()
        if row is None:
            return None
        if int(row[0]) != scope.project_revision:
            raise P6UserDefinedFieldValuePersistenceError("REVISION_CONFLICT")
        decoded = _decode_value(definition.data_type, str(row[2]), str(row[1]))
        result = P6UserDefinedFieldValue(scope, udf_id, object_type, object_id, decoded)
        result.validate_against(definition)
        return result
