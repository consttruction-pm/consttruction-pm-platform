from __future__ import annotations

import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_field_registry import P6FieldType, get_field
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    P6FieldRegistryPersistenceError,
    PersistedP6Field,
    SQLiteP6FieldRegistryRepository,
)


def _record(scope: BackendScope, field_id: str = "activity.activity_id") -> PersistedP6Field:
    return PersistedP6Field(
        scope=scope,
        registry_version="p6-field-registry.v1",
        field=get_field(field_id),
    )


def test_field_registry_persists_scope_and_typed_metadata() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FieldRegistryRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 7)

    saved = repository.upsert_field(_record(scope))
    loaded = repository.get_field(scope, "p6-field-registry.v1", "activity.activity_id")

    assert loaded == saved
    assert loaded is not None
    assert loaded.scope == scope
    assert loaded.field.data_type is P6FieldType.STRING


def test_field_registry_is_tenant_and_project_scoped() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FieldRegistryRepository(connection)
    scope = BackendScope("tenant-a", "project-a", 1)
    repository.upsert_field(_record(scope))

    assert repository.get_field(
        BackendScope("tenant-b", "project-a", 1),
        "p6-field-registry.v1",
        "activity.activity_id",
    ) is None
    assert repository.get_field(
        BackendScope("tenant-a", "project-b", 1),
        "p6-field-registry.v1",
        "activity.activity_id",
    ) is None


def test_field_registry_rejects_version_mismatch() -> None:
    repository = SQLiteP6FieldRegistryRepository(sqlite3.connect(":memory:"))
    with pytest.raises(P6FieldRegistryPersistenceError, match="UNSUPPORTED_REGISTRY_VERSION"):
        repository.get_field(
            BackendScope("tenant-a", "project-a", 1),
            "p6-field-registry.v2",
            "activity.activity_id",
        )


def test_field_registry_definitions_are_immutable() -> None:
    repository = SQLiteP6FieldRegistryRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 3)
    saved = _record(scope)
    repository.upsert_field(saved)

    field = saved.field
    changed = PersistedP6Field(
        scope=scope,
        registry_version=saved.registry_version,
        field=type(field)(
            field_id=field.field_id,
            subject_area=field.subject_area,
            p6_field=field.p6_field,
            display_name="Different Display Name",
            data_type=field.data_type,
            writable=field.writable,
            computed=field.computed,
            unit=field.unit,
        ),
    )
    with pytest.raises(P6FieldRegistryPersistenceError, match="IMMUTABLE_FIELD_DEFINITION"):
        repository.upsert_field(changed)


def test_field_registry_application_service_owns_transaction_boundary() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6FieldRegistryRepository(connection)
    service = P6FieldRegistryApplicationService(
        repository=repository,
        transaction_manager=SQLiteTransactionManager(connection),
    )
    scope = BackendScope("tenant-a", "project-a", 11)

    service.save_field(_record(scope))
    loaded = service.read_field(scope, "p6-field-registry.v1", "activity.activity_id")

    assert loaded is not None
    assert loaded.field.p6_field == "ActivityId"


def test_field_registry_subject_listing_is_deterministic() -> None:
    repository = SQLiteP6FieldRegistryRepository(sqlite3.connect(":memory:"))
    scope = BackendScope("tenant-a", "project-a", 1)

    repository.upsert_field(_record(scope, "activity.activity_name"))
    repository.upsert_field(_record(scope, "activity.activity_id"))
    repository.upsert_field(_record(scope, "project.id"))

    fields = repository.list_fields(scope, "p6-field-registry.v1", "Activity")
    assert [item.field.field_id for item in fields] == [
        "activity.activity_id",
        "activity.activity_name",
    ]
