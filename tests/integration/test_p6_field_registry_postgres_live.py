from __future__ import annotations

import os

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryPersistenceError,
    PersistedP6Field,
    PostgresP6FieldRegistryRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def record(scope: BackendScope, field_id: str = "activity.activity_id") -> PersistedP6Field:
    return PersistedP6Field(
        scope=scope,
        registry_version="p6-field-registry.v1",
        field=get_field(field_id),
    )


def test_postgres_field_registry_round_trip_isolation_and_revision():
    with connect() as conn:
        repo = PostgresP6FieldRegistryRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-field-pg", "project-field-pg", 1)
        item = record(scope)
        assert repo.upsert_field(item) == item
        assert repo.get_field(scope, "p6-field-registry.v1", item.field.field_id) == item
        assert repo.get_field(
            BackendScope("other-tenant", scope.project_id, 1),
            "p6-field-registry.v1",
            item.field.field_id,
        ) is None
        with pytest.raises(P6FieldRegistryPersistenceError, match="REVISION_CONFLICT"):
            repo.get_field(
                BackendScope(scope.tenant_id, scope.project_id, 2),
                "p6-field-registry.v1",
                item.field.field_id,
            )


def test_postgres_field_registry_rejects_mutation_and_preserves_committed_row():
    with connect() as conn:
        repo = PostgresP6FieldRegistryRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-field-rb", "project-field-rb", 1)
        item = record(scope)
        repo.upsert_field(item)
        conn.commit()
        changed = PersistedP6Field(
            scope=scope,
            registry_version=item.registry_version,
            field=type(item.field)(
                field_id=item.field.field_id,
                subject_area=item.field.subject_area,
                p6_field=item.field.p6_field,
                display_name="Changed",
                data_type=item.field.data_type,
                writable=item.field.writable,
                computed=item.field.computed,
                unit=item.field.unit,
            ),
        )
        with pytest.raises(P6FieldRegistryPersistenceError, match="IMMUTABLE_FIELD_DEFINITION"):
            repo.upsert_field(changed)
        conn.rollback()
        assert repo.get_field(scope, item.registry_version, item.field.field_id) == item


def test_postgres_field_registry_upsert_is_idempotent_and_preserves_typed_metadata():
    with connect() as conn:
        repo = PostgresP6FieldRegistryRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-field-idem", "project-field-idem", 3)
        item = PersistedP6Field(
            scope=scope,
            registry_version="p6-field-registry.v1",
            field=get_field("activity.activity_id"),
        )

        assert repo.upsert_field(item) == item
        assert repo.upsert_field(item) == item
        loaded = repo.get_field(scope, item.registry_version, item.field.field_id)

        assert loaded == item
        assert loaded is not None
        assert loaded.field.data_type == item.field.data_type
        assert loaded.field.reference_url == item.field.reference_url
        assert loaded.field.disposition == item.field.disposition
        assert loaded.field.read_only == item.field.read_only
        assert loaded.field.filterable == item.field.filterable
        assert loaded.field.orderable == item.field.orderable
        assert loaded.field.nullable == item.field.nullable


def test_postgres_field_registry_list_is_revision_and_subject_scoped():
    with connect() as conn:
        repo = PostgresP6FieldRegistryRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-field-list", "project-field-list", 4)
        repo.upsert_field(PersistedP6Field(scope=scope, registry_version="p6-field-registry.v1", field=get_field("activity.activity_name")))
        repo.upsert_field(PersistedP6Field(scope=scope, registry_version="p6-field-registry.v1", field=get_field("activity.activity_id")))
        repo.upsert_field(PersistedP6Field(scope=scope, registry_version="p6-field-registry.v1", field=get_field("project.id")))

        fields = repo.list_fields(scope, "p6-field-registry.v1", "Activity")
        assert [item.field.field_id for item in fields] == [
            "activity.activity_id",
            "activity.activity_name",
        ]
        assert repo.list_fields(
            BackendScope(scope.tenant_id, scope.project_id, scope.project_revision + 1),
            "p6-field-registry.v1",
        ) == ()