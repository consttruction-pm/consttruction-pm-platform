from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import P6FieldType
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldDefinition,
    SQLiteP6UserDefinedFieldRepository,
)
from construction_pm.p6_user_defined_field_values_repository import (
    P6DurationValue,
    P6UserDefinedFieldValue,
    P6UserDefinedFieldValueApplicationService,
    P6UserDefinedFieldValuePersistenceError,
    SQLiteP6UserDefinedFieldValueRepository,
)


def _definition(scope: BackendScope, udf_id: str, data_type: P6FieldType, **kwargs: object) -> P6UserDefinedFieldDefinition:
    return P6UserDefinedFieldDefinition(
        scope=scope,
        registry_version="p6-field-registry.v1",
        udf_id=udf_id,
        subject_area="Activity",
        display_name=udf_id,
        data_type=data_type,
        **kwargs,
    )


@pytest.mark.parametrize(
    ("data_type", "value"),
    [
        (P6FieldType.DATE, date(2026, 9, 28)),
        (P6FieldType.DATETIME, datetime(2026, 9, 28, 12, 30, tzinfo=timezone.utc)),
        (P6FieldType.DECIMAL, Decimal("123.4500")),
        (P6FieldType.BOOLEAN, True),
        (P6FieldType.ENUM, "active"),
    ],
)
def test_typed_udf_values_round_trip(data_type: P6FieldType, value: object) -> None:
    connection = sqlite3.connect(":memory:")
    definitions = SQLiteP6UserDefinedFieldRepository(connection)
    values = SQLiteP6UserDefinedFieldValueRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 3)
    definition = _definition(
        scope,
        f"udf.{data_type.value}",
        data_type,
        nullable=False,
        allowed_values=("draft", "active") if data_type is P6FieldType.ENUM else (),
    )
    definitions.upsert_definition(definition)

    saved = values.upsert_value(
        P6UserDefinedFieldValue(scope, definition.udf_id, "activity", "A-1", value),
        definition,
    )
    loaded = values.get_value(scope, definition.udf_id, "activity", "A-1", definition)

    assert loaded == saved
    assert type(loaded.value) is type(value)


def test_duration_round_trip_preserves_value_and_unit() -> None:
    connection = sqlite3.connect(":memory:")
    definitions = SQLiteP6UserDefinedFieldRepository(connection)
    values = SQLiteP6UserDefinedFieldValueRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 3)
    definition = _definition(scope, "udf.duration", P6FieldType.DURATION, unit="day", nullable=False)
    definitions.upsert_definition(definition)
    saved = P6UserDefinedFieldValue(
        scope, definition.udf_id, "activity", "A-1",
        P6DurationValue(Decimal("1.25"), "day"),
    )
    values.upsert_value(saved, definition)

    assert values.get_value(scope, definition.udf_id, "activity", "A-1", definition) == saved


def test_enum_value_must_match_definition() -> None:
    connection = sqlite3.connect(":memory:")
    definitions = SQLiteP6UserDefinedFieldRepository(connection)
    values = SQLiteP6UserDefinedFieldValueRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 3)
    definition = _definition(scope, "udf.status", P6FieldType.ENUM, nullable=False, allowed_values=("draft", "active"))
    definitions.upsert_definition(definition)

    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="INVALID_ENUM_VALUE"):
        values.upsert_value(P6UserDefinedFieldValue(scope, definition.udf_id, "activity", "A-1", "invalid"), definition)


def test_stale_revision_value_is_not_visible() -> None:
    connection = sqlite3.connect(":memory:")
    definitions = SQLiteP6UserDefinedFieldRepository(connection)
    values = SQLiteP6UserDefinedFieldValueRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 3)
    definition = _definition(scope, "udf.date", P6FieldType.DATE, nullable=False)
    definitions.upsert_definition(definition)
    values.upsert_value(P6UserDefinedFieldValue(scope, definition.udf_id, "activity", "A-1", date(2026, 9, 28)), definition)

    newer_scope = BackendScope("tenant-a", "project-a", 4)
    with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="UDF_NOT_FOUND|REVISION_CONFLICT"):
        P6UserDefinedFieldValueApplicationService(
            values, definitions, SQLiteTransactionManager(connection)
        ).read_value(newer_scope, definition.udf_id, "activity", "A-1")


def test_value_update_is_scoped_to_same_revision() -> None:
    connection = sqlite3.connect(":memory:")
    definitions = SQLiteP6UserDefinedFieldRepository(connection)
    values = SQLiteP6UserDefinedFieldValueRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 3)
    definition = _definition(scope, "udf.decimal", P6FieldType.DECIMAL)
    definitions.upsert_definition(definition)
    values.upsert_value(P6UserDefinedFieldValue(scope, definition.udf_id, "activity", "A-1", Decimal("1.00")), definition)
    updated = values.upsert_value(P6UserDefinedFieldValue(scope, definition.udf_id, "activity", "A-1", Decimal("2.00")), definition)

    assert updated.value == Decimal("2.00")


def test_value_application_service_owns_transaction_boundary() -> None:
    connection = sqlite3.connect(":memory:")
    definitions = SQLiteP6UserDefinedFieldRepository(connection)
    values = SQLiteP6UserDefinedFieldValueRepository(connection)
    service = P6UserDefinedFieldValueApplicationService(
        values, definitions, SQLiteTransactionManager(connection)
    )
    scope = BackendScope("tenant-a", "project-a", 3)
    definition = _definition(scope, "udf.bool", P6FieldType.BOOLEAN)
    definitions.upsert_definition(definition)

    service.save_value(P6UserDefinedFieldValue(scope, definition.udf_id, "activity", "A-1", True))
    assert service.read_value(scope, definition.udf_id, "activity", "A-1").value is True
