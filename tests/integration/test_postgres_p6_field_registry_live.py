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
from construction_pm.p6_field_registry import P6FieldType, get_field
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryPersistenceError,
    PostgresP6FieldRegistryRepository,
    PersistedP6Field,
)
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldDefinition,
    P6UserDefinedFieldPersistenceError,
    PostgresP6UserDefinedFieldRepository,
)
from construction_pm.p6_user_defined_field_values_repository import (
    P6DurationValue,
    P6UserDefinedFieldValue,
    PostgresP6UserDefinedFieldValueRepository,
    P6UserDefinedFieldValuePersistenceError,
)


def scope() -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"live-tenant-{suffix}", f"live-project-{suffix}", 3)


def test_p6_postgres_field_registry_round_trip_isolation_revision_and_rollback() -> None:
    s = scope()
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6FieldRegistryRepository(connection)
        repository.initialize()
        connection.commit()

        record = PersistedP6Field(s, "p6-field-registry.v1", get_field("activity.activity_id"))
        with PostgresTransactionManager(connection).transaction():
            assert repository.upsert_field(record) == record

        assert repository.get_field(s, "p6-field-registry.v1", record.field.field_id) == record
        assert repository.get_field(
            BackendScope(s.tenant_id + "-other", s.project_id, s.project_revision),
            "p6-field-registry.v1",
            record.field.field_id,
        ) is None

        with pytest.raises(P6FieldRegistryPersistenceError, match="REVISION_CONFLICT"):
            repository.get_field(
                BackendScope(s.tenant_id, s.project_id, s.project_revision + 1),
                "p6-field-registry.v1",
                record.field.field_id,
            )

        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                repository.upsert_field(
                    PersistedP6Field(s, "p6-field-registry.v1", get_field("activity.activity_name"))
                )
                raise RuntimeError("FORCED_ROLLBACK")

        assert repository.get_field(s, "p6-field-registry.v1", "activity.activity_name") is None


def test_p6_postgres_udf_definition_is_immutable_and_revision_safe() -> None:
    s = scope()
    definition = P6UserDefinedFieldDefinition(
        scope=s,
        registry_version="p6-field-registry.v1",
        udf_id="udf.activity.status",
        subject_area="Activity",
        display_name="Status",
        data_type=P6FieldType.ENUM,
        nullable=False,
        allowed_values=("draft", "active"),
    )
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6UserDefinedFieldRepository(connection)
        repository.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            assert repository.upsert_definition(definition) == definition
        assert repository.get_definition(s, definition.registry_version, definition.udf_id) == definition

        changed = P6UserDefinedFieldDefinition(
            **{**definition.__dict__, "display_name": "Changed"}
        )
        with pytest.raises(P6UserDefinedFieldPersistenceError, match="IMMUTABLE_UDF_DEFINITION"):
            repository.upsert_definition(changed)

        with pytest.raises(P6UserDefinedFieldPersistenceError, match="REVISION_CONFLICT"):
            repository.get_definition(
                BackendScope(s.tenant_id, s.project_id, s.project_revision + 1),
                definition.registry_version,
                definition.udf_id,
            )


def test_p6_postgres_typed_udf_values_round_trip_and_update() -> None:
    s = scope()
    definition = P6UserDefinedFieldDefinition(
        scope=s,
        registry_version="p6-field-registry.v1",
        udf_id="udf.activity.duration",
        subject_area="Activity",
        display_name="Duration",
        data_type=P6FieldType.DURATION,
        nullable=False,
        unit="day",
    )
    with psycopg.connect(DSN) as connection:
        definitions = PostgresP6UserDefinedFieldRepository(connection)
        values = PostgresP6UserDefinedFieldValueRepository(connection)
        definitions.initialize()
        values.initialize()
        connection.commit()

        definitions.upsert_definition(definition)
        first = P6UserDefinedFieldValue(
            s, definition.udf_id, "activity", "A-1",
            P6DurationValue(Decimal("1.25"), "day"),
        )
        with PostgresTransactionManager(connection).transaction():
            values.upsert_value(first, definition)
        assert values.get_value(s, definition.udf_id, "activity", "A-1", definition) == first

        second = P6UserDefinedFieldValue(
            s, definition.udf_id, "activity", "A-1",
            P6DurationValue(Decimal("2.50"), "day"),
        )
        with PostgresTransactionManager(connection).transaction():
            values.upsert_value(second, definition)
        assert values.get_value(s, definition.udf_id, "activity", "A-1", definition) == second


def test_p6_postgres_typed_date_value_preserves_datetime_type_boundary() -> None:
    s = scope()
    definition = P6UserDefinedFieldDefinition(
        scope=s,
        registry_version="p6-field-registry.v1",
        udf_id="udf.activity.date",
        subject_area="Activity",
        display_name="Start Date",
        data_type=P6FieldType.DATE,
        nullable=False,
    )
    with psycopg.connect(DSN) as connection:
        definitions = PostgresP6UserDefinedFieldRepository(connection)
        values = PostgresP6UserDefinedFieldValueRepository(connection)
        definitions.initialize()
        values.initialize()
        connection.commit()
        definitions.upsert_definition(definition)

        saved = P6UserDefinedFieldValue(
            s, definition.udf_id, "activity", "A-2", date(2026, 9, 28)
        )
        values.upsert_value(saved, definition)
        loaded = values.get_value(s, definition.udf_id, "activity", "A-2", definition)
        assert loaded == saved
        assert type(loaded.value) is date
