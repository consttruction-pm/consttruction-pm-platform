from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_field_registry import P6FieldType
from construction_pm.p6_user_defined_field_values_repository import (
    P6DurationValue,
    P6UserDefinedFieldValue,
    P6UserDefinedFieldValuePersistenceError,
    PostgresP6UserDefinedFieldValueRepository,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldDefinition,
    PostgresP6UserDefinedFieldRepository,
)


def scope(revision: int = 3) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"udfv-tenant-{suffix}", f"udfv-project-{suffix}", revision)


def definition(current_scope: BackendScope, udf_id: str, data_type: P6FieldType, **kwargs: object) -> P6UserDefinedFieldDefinition:
    return P6UserDefinedFieldDefinition(
        scope=current_scope,
        registry_version="p6-field-registry.v1",
        udf_id=udf_id,
        subject_area="Activity",
        display_name=udf_id,
        data_type=data_type,
        **kwargs,
    )


def test_postgres_typed_udf_value_round_trip_and_scope_isolation() -> None:
    current_scope = scope()
    udf = definition(current_scope, "udf.decimal", P6FieldType.DECIMAL)
    value = P6UserDefinedFieldValue(
        current_scope, udf.udf_id, "activity", "A-1", Decimal("123.4500")
    )

    with psycopg.connect(DSN) as connection:
        definitions = PostgresP6UserDefinedFieldRepository(connection)
        values = PostgresP6UserDefinedFieldValueRepository(connection)
        definitions.initialize()
        values.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            definitions.upsert_definition(udf)
            values.upsert_value(value, udf)

        assert values.get_value(current_scope, udf.udf_id, "activity", "A-1", udf) == value
        assert values.get_value(
            BackendScope(current_scope.tenant_id + "-other", current_scope.project_id, current_scope.project_revision),
            udf.udf_id,
            "activity",
            "A-1",
            udf,
        ) is None


def test_postgres_udf_value_preserves_duration_and_datetime_types() -> None:
    current_scope = scope()
    definitions = [
        definition(current_scope, "udf.duration", P6FieldType.DURATION, unit="day"),
        definition(current_scope, "udf.datetime", P6FieldType.DATETIME),
    ]
    values_to_save = [
        P6UserDefinedFieldValue(
            current_scope, "udf.duration", "activity", "A-1",
            P6DurationValue(Decimal("1.25"), "day"),
        ),
        P6UserDefinedFieldValue(
            current_scope, "udf.datetime", "activity", "A-1",
            datetime(2026, 9, 28, 12, 30, tzinfo=timezone.utc),
        ),
    ]

    with psycopg.connect(DSN) as connection:
        definitions_repo = PostgresP6UserDefinedFieldRepository(connection)
        values_repo = PostgresP6UserDefinedFieldValueRepository(connection)
        definitions_repo.initialize()
        values_repo.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            for item in definitions:
                definitions_repo.upsert_definition(item)
            for value, item in zip(values_to_save, definitions):
                values_repo.upsert_value(value, item)

        assert values_repo.get_value(current_scope, "udf.duration", "activity", "A-1", definitions[0]) == values_to_save[0]
        assert values_repo.get_value(current_scope, "udf.datetime", "activity", "A-1", definitions[1]) == values_to_save[1]


def test_postgres_udf_value_rollback_and_revision_conflict() -> None:
    current_scope = scope()
    udf = definition(current_scope, "udf.date", P6FieldType.DATE)
    value = P6UserDefinedFieldValue(
        current_scope, udf.udf_id, "activity", "A-1", date(2026, 9, 28)
    )

    with psycopg.connect(DSN) as connection:
        definitions = PostgresP6UserDefinedFieldRepository(connection)
        values = PostgresP6UserDefinedFieldValueRepository(connection)
        definitions.initialize()
        values.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            definitions.upsert_definition(udf)

        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                values.upsert_value(value, udf)
                raise RuntimeError("FORCED_ROLLBACK")

        assert values.get_value(current_scope, udf.udf_id, "activity", "A-1", udf) is None

        with pytest.raises(P6UserDefinedFieldValuePersistenceError, match="REVISION_CONFLICT"):
            values.get_value(
                BackendScope(current_scope.tenant_id, current_scope.project_id, current_scope.project_revision + 1),
                udf.udf_id,
                "activity",
                "A-1",
                udf,
            )
