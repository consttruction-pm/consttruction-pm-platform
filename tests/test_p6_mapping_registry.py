from __future__ import annotations

import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition, P6MappingFormat, P6MappingRegistryError,
    P6MappingStatus, PersistedP6Mapping, SQLiteP6MappingRegistryRepository,
)


def scope(revision: int = 1) -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=revision)


def record(revision: int = 1, mapping_id: str = "activity.code") -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope=scope(revision),
        definition=P6MappingDefinition(
            mapping_id=mapping_id, registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT, subject_area="Activity",
            source_field="task_code", canonical_field="activity.code",
            status=P6MappingStatus.SUPPORTED, source_type="string", canonical_type="string",
        ),
    )


def test_round_trip_and_deterministic_list() -> None:
    repo = SQLiteP6MappingRegistryRepository(sqlite3.connect(":memory:"))
    repo.upsert_mapping(record("".__len__() + 1))
    repo.upsert_mapping(record(mapping_id="activity.name"))
    assert [x.definition.mapping_id for x in repo.list_mappings(scope())] == ["activity.code", "activity.name"]
    assert repo.get_mapping(scope(), "activity.code") == record()


def test_immutable_and_stale_revision() -> None:
    repo = SQLiteP6MappingRegistryRepository(sqlite3.connect(":memory:"))
    repo.upsert_mapping(record())
    with pytest.raises(P6MappingRegistryError, match="IMMUTABLE_MAPPING_DEFINITION"):
        repo.upsert_mapping(record(mapping_id="activity.code"))
    with pytest.raises(P6MappingRegistryError, match="REVISION_CONFLICT"):
        repo.get_mapping(scope(2), "activity.code")


def test_scope_isolation() -> None:
    repo = SQLiteP6MappingRegistryRepository(sqlite3.connect(":memory:"))
    repo.upsert_mapping(record())
    other = PersistedP6Mapping(scope=BackendScope(tenant_id="t2", project_id="p1", project_revision=1),
                                definition=record().definition)
    assert repo.get_mapping(other.scope, "activity.code") is None


def test_unsupported_policy_is_explicit() -> None:
    repo = SQLiteP6MappingRegistryRepository(sqlite3.connect(":memory:"))
    rec = record()
    rec = PersistedP6Mapping(scope=rec.scope, definition=P6MappingDefinition(
        **{**rec.definition.__dict__, "status": P6MappingStatus.UNSUPPORTED_PRESERVE}
    ))
    repo.upsert_mapping(rec)
    assert repo.get_mapping(scope(), "activity.code").definition.status == P6MappingStatus.UNSUPPORTED_PRESERVE


def test_invalid_registry_version_fails_closed() -> None:
    rec = record()
    with pytest.raises(P6MappingRegistryError, match="UNSUPPORTED_REGISTRY_VERSION"):
        PersistedP6Mapping(
            scope=rec.scope,
            definition=P6MappingDefinition(**{**rec.definition.__dict__, "registry_version": "p6-field-registry.v2"}),
        ).validate()
