from __future__ import annotations

import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import P6FieldType
from construction_pm.p6_user_defined_fields_repository import (
    P6UserDefinedFieldApplicationService,
    P6UserDefinedFieldDefinition,
    P6UserDefinedFieldPersistenceError,
    SQLiteP6UserDefinedFieldRepository,
)


def _definition(
    scope: BackendScope,
    udf_id: str = "udf.activity.contract_status",
) -> P6UserDefinedFieldDefinition:
    return P6UserDefinedFieldDefinition(
        scope=scope,
        registry_version="p6-field-registry.v1",
        udf_id=udf_id,
        subject_area="Activity",
        display_name="Contract Status",
        data_type=P6FieldType.ENUM,
        writable=True,
        nullable=False,
        allowed_values=("draft", "active", "closed"),
    )


def test_udf_round_trip_preserves_typed_definition_and_scope() -> None:
    repository = SQLiteP6UserDefinedFieldRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 7)

    saved = repository.upsert_definition(_definition(scope))
    loaded = repository.get_definition(scope, "p6-field-registry.v1", saved.udf_id)

    assert loaded == saved
    assert loaded is not None
    assert loaded.data_type is P6FieldType.ENUM
    assert loaded.allowed_values == ("draft", "active", "closed")


def test_udf_isolation_by_tenant_and_project() -> None:
    repository = SQLiteP6UserDefinedFieldRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 1)
    repository.upsert_definition(_definition(scope))

    assert repository.get_definition(
        BackendScope("tenant-b", "project-a", 1),
        "p6-field-registry.v1",
        "udf.activity.contract_status",
    ) is None
    assert repository.get_definition(
        BackendScope("tenant-a", "project-b", 1),
        "p6-field-registry.v1",
        "udf.activity.contract_status",
    ) is None


def test_udf_rejects_stale_revision_reads() -> None:
    repository = SQLiteP6UserDefinedFieldRepository(sqlite3.connect(":memory:"))
    repository.upsert_definition(_definition(BackendScope("tenant-a", "project-a", 3)))

    with pytest.raises(P6UserDefinedFieldPersistenceError, match="REVISION_CONFLICT"):
        repository.get_definition(
            BackendScope("tenant-a", "project-a", 4),
            "p6-field-registry.v1",
            "udf.activity.contract_status",
        )


def test_udf_rejects_revision_change_for_same_definition() -> None:
    repository = SQLiteP6UserDefinedFieldRepository(sqlite3.connect(":memory:"))
    repository.upsert_definition(_definition(BackendScope("tenant-a", "project-a", 3)))

    with pytest.raises(P6UserDefinedFieldPersistenceError, match="REVISION_CONFLICT"):
        repository.upsert_definition(_definition(BackendScope("tenant-a", "project-a", 4)))


def test_udf_definitions_are_immutable() -> None:
    repository = SQLiteP6UserDefinedFieldRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 3)
    saved = _definition(scope)
    repository.upsert_definition(saved)
    changed = P6UserDefinedFieldDefinition(
        scope=scope,
        registry_version=saved.registry_version,
        udf_id=saved.udf_id,
        subject_area=saved.subject_area,
        display_name="Changed",
        data_type=saved.data_type,
        writable=saved.writable,
        nullable=saved.nullable,
        unit=saved.unit,
        allowed_values=saved.allowed_values,
    )

    with pytest.raises(P6UserDefinedFieldPersistenceError, match="IMMUTABLE_UDF_DEFINITION"):
        repository.upsert_definition(changed)


def test_udf_rejects_non_enum_allowed_values() -> None:
    with pytest.raises(P6UserDefinedFieldPersistenceError, match="INVALID_ALLOWED_VALUES"):
        _definition(BackendScope("tenant-a", "project-a", 1)).__class__(
            scope=BackendScope("tenant-a", "project-a", 1),
            registry_version="p6-field-registry.v1",
            udf_id="udf.activity.percent",
            subject_area="Activity",
            display_name="Percent",
            data_type=P6FieldType.PERCENTAGE,
            allowed_values=("10", "20"),
        ).validate()


def test_udf_application_service_owns_transaction_boundary() -> None:
    connection = sqlite3.connect(":memory:")
    service = P6UserDefinedFieldApplicationService(
        repository=SQLiteP6UserDefinedFieldRepository(connection),
        transaction_manager=SQLiteTransactionManager(connection),
    )
    scope = BackendScope("tenant-a", "project-a", 11)

    service.save_definition(_definition(scope))
    loaded = service.read_definition(scope, "p6-field-registry.v1", "udf.activity.contract_status")

    assert loaded is not None
    assert loaded.display_name == "Contract Status"


def test_udf_subject_listing_is_deterministic() -> None:
    repository = SQLiteP6UserDefinedFieldRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 1)
    repository.upsert_definition(_definition(scope, "udf.activity.z"))
    repository.upsert_definition(_definition(scope, "udf.activity.a"))

    assert [item.udf_id for item in repository.list_definitions(
        scope, "p6-field-registry.v1", "Activity"
    )] == ["udf.activity.a", "udf.activity.z"]
