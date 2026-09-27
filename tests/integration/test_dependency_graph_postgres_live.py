from datetime import datetime, timezone
import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.dependency_graph_persistence import (
    DependencyIdempotencyReuse,
    DependencyLink,
    DependencyRevisionConflict,
    PostgresDependencyGraphStore,
)


def test_dependency_graph_round_trip_persists_revision_and_audit() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"live-tenant-{suffix}"
    project_id = f"live-project-{suffix}"
    resource_id = f"live-dependency-{suffix}"
    idempotency_key = f"live-idem-{suffix}"
    created_at = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    link = DependencyLink(
        resource_id=resource_id,
        tenant_id=tenant_id,
        project_id=project_id,
        revision=1,
        source_resource_id=f"schedule:task-{suffix}",
        target_resource_id=f"rfi:rfi-{suffix}",
        dependency_type="schedule_to_rfi",
        metadata={"relation": "blocks"},
    )

    with psycopg.connect(DSN) as connection:
        store = PostgresDependencyGraphStore(connection)
        store.initialize()
        store.ensure_project(tenant_id, project_id)
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            persisted = store.persist(
                link,
                expected_graph_revision=0,
                idempotency_key=idempotency_key,
                actor_id="requester-1",
                occurred_at=created_at,
            )

        assert persisted.graph_revision == 1
        loaded = store.get(tenant_id, project_id, resource_id)
        assert loaded == persisted

        replay = store.persist(
            link,
            expected_graph_revision=0,
            idempotency_key=idempotency_key,
            actor_id="requester-1",
            occurred_at=created_at,
        )
        assert replay == persisted

        history = store.history(tenant_id, project_id, resource_id)
        assert [(event.graph_revision, event.event_type, event.actor_id) for event in history] == [
            (1, "created", "requester-1"),
        ]

        connection.rollback()

        with PostgresTransactionManager(connection).transaction():
            with pytest.raises(DependencyRevisionConflict):
                store.persist(
                    DependencyLink(
                        resource_id=f"live-dependency-2-{suffix}",
                        tenant_id=tenant_id,
                        project_id=project_id,
                        revision=1,
                        source_resource_id=f"schedule:task-2-{suffix}",
                        target_resource_id=f"change:change-{suffix}",
                        dependency_type="schedule_to_change",
                        metadata={"relation": "blocks"},
                    ),
                    expected_graph_revision=0,
                    idempotency_key=f"live-idem-2-{suffix}",
                    actor_id="requester-2",
                    occurred_at=created_at,
                )

        connection.rollback()

        with PostgresTransactionManager(connection).transaction():
            with pytest.raises(DependencyIdempotencyReuse):
                store.persist(
                    DependencyLink(
                        resource_id=resource_id,
                        tenant_id=tenant_id,
                        project_id=project_id,
                        revision=1,
                        source_resource_id=f"schedule:task-{suffix}",
                        target_resource_id=f"change:change-{suffix}",
                        dependency_type="schedule_to_change",
                        metadata={"relation": "depends_on"},
                    ),
                    expected_graph_revision=1,
                    idempotency_key=idempotency_key,
                    actor_id="requester-1",
                    occurred_at=created_at,
                )

        connection.rollback()


def test_dependency_graph_live_transaction_rolls_back_revision_link_and_audit() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"rollback-tenant-{suffix}"
    project_id = f"rollback-project-{suffix}"
    resource_id = f"rollback-dependency-{suffix}"
    created_at = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
    link = DependencyLink(
        resource_id=resource_id,
        tenant_id=tenant_id,
        project_id=project_id,
        revision=1,
        source_resource_id=f"schedule:task-{suffix}",
        target_resource_id=f"rfi:rfi-{suffix}",
        dependency_type="schedule_to_rfi",
        metadata={"relation": "blocks"},
    )

    with psycopg.connect(DSN) as connection:
        store = PostgresDependencyGraphStore(connection)
        store.initialize()
        store.ensure_project(tenant_id, project_id)
        connection.commit()

        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                persisted = store.persist(
                    link,
                    expected_graph_revision=0,
                    idempotency_key=f"rollback-idem-{suffix}",
                    actor_id="requester-rollback",
                    occurred_at=created_at,
                )
                assert persisted.graph_revision == 1
                raise RuntimeError("FORCED_ROLLBACK")

        assert store.get(tenant_id, project_id, resource_id) is None
        assert store.history(tenant_id, project_id, resource_id) == []
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT revision FROM project_dependency_revisions WHERE tenant_id = %s AND project_id = %s",
                (tenant_id, project_id),
            )
            assert cursor.fetchone()[0] == 0
