import os
import uuid
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
    P6MappingRegistryError,
    PostgresP6MappingRegistryRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def mapping(scope: BackendScope, mapping_id: str = "activity.start") -> PersistedP6Mapping:
    return PersistedP6Mapping(
        scope,
        P6MappingDefinition(
            mapping_id=mapping_id,
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="task_start_date",
            canonical_field="activity.planned_start",
            status=P6MappingStatus.SUPPORTED,
            source_type="date",
            canonical_type="date",
        ),
    )


def test_postgres_round_trip_list_isolation_and_revision():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-map-{suffix}", f"project-map-{suffix}", 1)
    with connect() as conn:
        repo = PostgresP6MappingRegistryRepository(conn)
        repo.initialize()
        item = mapping(scope)
        assert repo.upsert_mapping(item) == item
        assert repo.get_mapping(scope, item.definition.mapping_id) == item
        assert repo.list_mappings(scope) == (item,)
        assert repo.get_mapping(BackendScope("other", scope.project_id, 1), item.definition.mapping_id) is None
        with pytest.raises(P6MappingRegistryError, match="REVISION_CONFLICT"):
            repo.get_mapping(BackendScope(scope.tenant_id, scope.project_id, 2), item.definition.mapping_id)


def test_postgres_immutable_replay_and_conflict():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-map-immut-{suffix}", f"project-map-immut-{suffix}", 1)
    with connect() as conn:
        repo = PostgresP6MappingRegistryRepository(conn)
        repo.initialize()
        item = mapping(scope)
        assert repo.upsert_mapping(item) == item
        assert repo.upsert_mapping(item) == item
        changed = PersistedP6Mapping(
            scope,
            P6MappingDefinition(
                mapping_id=item.definition.mapping_id,
                registry_version=item.definition.registry_version,
                format=P6MappingFormat.PRIMAVERA_XML,
                subject_area=item.definition.subject_area,
                source_field=item.definition.source_field,
                canonical_field=item.definition.canonical_field,
                status=item.definition.status,
                source_type=item.definition.source_type,
                canonical_type=item.definition.canonical_type,
            ),
        )
        with pytest.raises(P6MappingRegistryError, match="IMMUTABLE_MAPPING_DEFINITION"):
            repo.upsert_mapping(changed)
        with pytest.raises(P6MappingRegistryError, match="REVISION_CONFLICT"):
            repo.upsert_mapping(mapping(BackendScope(scope.tenant_id, scope.project_id, 2)))


def test_postgres_rollback():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-map-rb-{suffix}", f"project-map-rb-{suffix}", 1)
    with connect() as conn:
        repo = PostgresP6MappingRegistryRepository(conn)
        repo.initialize()
        conn.commit()
        try:
            repo.upsert_mapping(mapping(scope))
            raise RuntimeError("force rollback")
        except RuntimeError:
            conn.rollback()
        assert repo.get_mapping(scope, "activity.start") is None
