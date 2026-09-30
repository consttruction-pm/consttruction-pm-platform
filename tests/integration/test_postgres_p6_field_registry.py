from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryPersistenceError,
    PersistedP6Field,
    PostgresP6FieldRegistryRepository,
)


def scope(revision: int = 3) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"field-tenant-{suffix}", f"field-project-{suffix}", revision)


def record(current_scope: BackendScope, field_id: str = "activity.activity_id") -> PersistedP6Field:
    return PersistedP6Field(
        scope=current_scope,
        registry_version="p6-field-registry.v1",
        field=get_field(field_id),
    )


def test_postgres_field_round_trip_and_immutability() -> None:
    current_scope = scope()
    original = record(current_scope)
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6FieldRegistryRepository(connection)
        repository.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            repository.upsert_field(original)
        assert repository.get_field(
            current_scope, "p6-field-registry.v1", original.field.field_id
        ) == original
        changed_field = type(original.field)(
            field_id=original.field.field_id,
            subject_area=original.field.subject_area,
            p6_field=original.field.p6_field,
            display_name="Changed",
            data_type=original.field.data_type,
            writable=original.field.writable,
            computed=original.field.computed,
            unit=original.field.unit,
        )
        changed = PersistedP6Field(current_scope, original.registry_version, changed_field)
        with pytest.raises(P6FieldRegistryPersistenceError, match="IMMUTABLE_FIELD_DEFINITION"):
            with PostgresTransactionManager(connection).transaction():
                repository.upsert_field(changed)


def test_postgres_field_concurrent_identical_upsert_is_idempotent() -> None:
    current_scope = scope()
    original = record(current_scope, field_id="activity.concurrent")
    barrier = threading.Barrier(2)

    def save() -> PersistedP6Field:
        with psycopg.connect(DSN) as connection:
            repository = PostgresP6FieldRegistryRepository(connection)
            repository.initialize()
            connection.commit()
            barrier.wait(timeout=5)
            with PostgresTransactionManager(connection).transaction():
                return repository.upsert_field(original)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]

    assert results == [original, original]
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6FieldRegistryRepository(connection)
        assert repository.get_field(
            current_scope, "p6-field-registry.v1", original.field.field_id
        ) == original
