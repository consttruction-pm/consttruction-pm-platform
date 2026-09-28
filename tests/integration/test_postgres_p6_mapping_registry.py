from __future__ import annotations

import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition, P6MappingFormat, P6MappingRegistryError,
    P6MappingStatus, PersistedP6Mapping, PostgresP6MappingRegistryRepository,
)


def scope(revision: int = 3) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"map-tenant-{suffix}", f"map-project-{suffix}", revision)


def record(current_scope: BackendScope, mapping_id: str = "activity.code") -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope=current_scope,
        definition=P6MappingDefinition(
            mapping_id=mapping_id, registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT, subject_area="Activity",
            source_field="task_code", canonical_field="activity.code",
            status=P6MappingStatus.SUPPORTED, source_type="string", canonical_type="string",
        ),
    )


def test_postgres_mapping_round_trip_isolation_and_revision_conflict() -> None:
    current_scope = scope()
    original = record(current_scope)
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6MappingRegistryRepository(connection)
        repository.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            repository.upsert_mapping(original)
        assert repository.get_mapping(current_scope, original.definition.mapping_id) == original
        assert repository.get_mapping(
            BackendScope(current_scope.tenant_id + "-other", current_scope.project_id, current_scope.project_revision),
            original.definition.mapping_id,
        ) is None
        with pytest.raises(P6MappingRegistryError, match="REVISION_CONFLICT"):
            repository.get_mapping(
                BackendScope(current_scope.tenant_id, current_scope.project_id, current_scope.project_revision + 1),
                original.definition.mapping_id,
            )


def test_postgres_mapping_immutability() -> None:
    current_scope = scope()
    original = record(current_scope)
    changed = PersistedP6Mapping(
        scope=current_scope,
        definition=P6MappingDefinition(**{**original.definition.__dict__, "canonical_field": "activity.changed"}),
    )
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6MappingRegistryRepository(connection)
        repository.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            repository.upsert_mapping(original)
        with pytest.raises(P6MappingRegistryError, match="IMMUTABLE_MAPPING_DEFINITION"):
            with PostgresTransactionManager(connection).transaction():
                repository.upsert_mapping(changed)


def test_postgres_mapping_rollback() -> None:
    current_scope = scope()
    original = record(current_scope)
    with psycopg.connect(DSN) as connection:
        repository = PostgresP6MappingRegistryRepository(connection)
        repository.initialize()
        connection.commit()
        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                repository.upsert_mapping(original)
                raise RuntimeError("FORCED_ROLLBACK")
        assert repository.get_mapping(current_scope, original.definition.mapping_id) is None
