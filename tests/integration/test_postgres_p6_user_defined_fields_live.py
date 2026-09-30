from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
import uuid

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_field_registry import P6FieldType
from construction_pm.p6_user_defined_field_values_repository import (
    P6DurationValue,
    P6UserDefinedFieldValue,
    P6UserDefinedFieldValuePersistenceError,
    PostgresP6UserDefinedFieldValueRepository,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldDefinition,
    P6UserDefinedFieldPersistenceError,
    PostgresP6UserDefinedFieldRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def definition(
    scope: BackendScope,
    *,
    udf_id: str = "custom.phase",
    data_type: P6FieldType = P6FieldType.ENUM,
) -> P6UserDefinedFieldDefinition:
    return P6UserDefinedFieldDefinition(
        scope=scope,
        registry_version="p6-field-registry.v1",
        udf_id=udf_id,
        subject_area="Activity",
        display_name="Custom Phase",
        data_type=data_type,
        writable=True,
        nullable=True,
        unit=None,
        allowed_values=("PLANNING", "EXECUTION", "CLOSED") if data_type is P6FieldType.ENUM else (),
    )


def test_postgres_udf_definition_round_trip_list_isolation_and_revision():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-udf-{suffix}", f"project-udf-{suffix}", 1)
    with connect() as conn:
        repo = PostgresP6UserDefinedFieldRepository(conn)
        repo.initialize()
        item = definition(scope)
        assert repo.upsert_definition(item) == item
        assert repo.get_definition(scope, item.registry_version, item.udf_id) == item
        assert repo.list_definitions(scope, item.registry_version, "Activity") == (item,)
        assert repo.get_definition(
            BackendScope("other", scope.project_id, 1),
            item.registry_version,
            item.udf_id,
        ) is None
        with pytest.raises(P6UserDefinedFieldPersistenceError, match="REVISION_CONFLICT"):
            repo.get_definition(
                BackendScope(scope.tenant_id, scope.project_id, 2),
                item.registry_version,
                item.udf_id,
            )


def test_postgres_udf_definition_is_immutable_and_replay_safe():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-udf-immut-{suffix}", f"project-udf-immut-{suffix}", 1)
    with connect() as conn:
        repo = PostgresP6UserDefinedFieldRepository(conn)
        repo.initialize()
        item = definition(scope)
        assert repo.upsert_definition(item) == item
        assert repo.upsert_definition(item) == item
        changed = P6UserDefinedFieldDefinition(
            scope=scope,
            registry_version=item.registry_version,
            udf_id=item.udf_id,
            subject_area=item.subject_area,
            display_name="Changed",
            data_type=item.data_type,
            writable=item.writable,
            nullable=item.nullable,
            unit=item.unit,
            allowed_values=item.allowed_values,
        )
        with pytest.raises(P6UserDefinedFieldPersistenceError, match="IMMUTABLE_UDF_DEFINITION"):
            repo.upsert_definition(changed)
        assert repo.get_definition(scope, item.registry_version, item.udf_id) == item


def test_postgres_udf_typed_values_round_trip_and_rollback():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-udf-value-{suffix}", f"project-udf-value-{suffix}", 1)
    with connect() as conn:
        definitions = PostgresP6UserDefinedFieldRepository(conn)
        values = PostgresP6UserDefinedFieldValueRepository(conn)
        definitions.initialize()
        values.initialize()

        enum_definition = definition(scope)
        decimal_definition = definition(
            scope, udf_id="custom.amount", data_type=P6FieldType.DECIMAL
        )
        definitions.upsert_definition(enum_definition)
        definitions.upsert_definition(decimal_definition)

        enum_value = P6UserDefinedFieldValue(
            scope, enum_definition.udf_id, "Activity", "A-100", "EXECUTION"
        )
        decimal_value = P6UserDefinedFieldValue(
            scope, decimal_definition.udf_id, "Activity", "A-100", Decimal("123.45")
        )
        assert values.upsert_value(enum_value, enum_definition) == enum_value
        assert values.upsert_value(decimal_value, decimal_definition) == decimal_value
        assert values.get_value(
            scope, enum_definition.udf_id, "Activity", "A-100", enum_definition
        ) == enum_value
        assert values.get_value(
            scope, decimal_definition.udf_id, "Activity", "A-100", decimal_definition
        ) == decimal_value

        datetime_definition = definition(
            scope, udf_id="custom.timestamp", data_type=P6FieldType.DATETIME
        )
        definitions.upsert_definition(datetime_definition)
        timestamp_value = P6UserDefinedFieldValue(
            scope,
            datetime_definition.udf_id,
            "Activity",
            "A-100",
            datetime(2026, 10, 1, 8, 30, tzinfo=timezone.utc),
        )
        assert values.upsert_value(timestamp_value, datetime_definition) == timestamp_value

        duration_definition = definition(
            scope, udf_id="custom.duration", data_type=P6FieldType.DURATION
        )
        definitions.upsert_definition(duration_definition)
        duration_value = P6UserDefinedFieldValue(
            scope,
            duration_definition.udf_id,
            "Activity",
            "A-100",
            P6DurationValue(Decimal("2.5"), "working-day"),
        )
        assert values.upsert_value(duration_value, duration_definition) == duration_value
        assert values.get_value(
            scope, duration_definition.udf_id, "Activity", "A-100", duration_definition
        ) == duration_value

        rollback_definition = definition(
            scope, udf_id="custom.rollback", data_type=P6FieldType.INTEGER
        )
        definitions.upsert_definition(rollback_definition)
        conn.commit()
        try:
            rollback_value = P6UserDefinedFieldValue(
                scope, rollback_definition.udf_id, "Activity", "A-100", 7
            )
            values.upsert_value(rollback_value, rollback_definition)
            raise RuntimeError("force rollback")
        except RuntimeError:
            conn.rollback()
        assert values.get_value(
            scope,
            rollback_definition.udf_id,
            "Activity",
            "A-100",
            rollback_definition,
        ) is None


def test_postgres_udf_value_rejects_scope_mismatch():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-udf-scope-{suffix}", f"project-udf-scope-{suffix}", 1)
    other_scope = BackendScope(f"other-tenant-{suffix}", scope.project_id, 1)
    with connect() as conn:
        definitions = PostgresP6UserDefinedFieldRepository(conn)
        values = PostgresP6UserDefinedFieldValueRepository(conn)
        definitions.initialize()
        values.initialize()
        item = definition(scope)
        definitions.upsert_definition(item)
        invalid = P6UserDefinedFieldValue(
            other_scope, item.udf_id, "Activity", "A-100", "EXECUTION"
        )
        with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="REVISION_CONFLICT"):
            values.upsert_value(invalid, item)
