from datetime import datetime, timezone
import os
import uuid
import threading

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

        with PostgresTransactionManager(connection).transaction():
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


def test_dependency_graph_live_idempotency_reuse_does_not_advance_revision() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"reuse-tenant-{suffix}"
    project_id = f"reuse-project-{suffix}"
    resource_id = f"reuse-dependency-{suffix}"
    key = f"reuse-idem-{suffix}"
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
            store.persist(
                link,
                expected_graph_revision=0,
                idempotency_key=key,
                actor_id="requester-1",
                occurred_at=created_at,
            )

        with PostgresTransactionManager(connection).transaction():
            with pytest.raises(DependencyIdempotencyReuse):
                store.persist(
                    DependencyLink(
                        resource_id=f"{resource_id}-other",
                        tenant_id=tenant_id,
                        project_id=project_id,
                        revision=1,
                        source_resource_id=f"schedule:other-{suffix}",
                        target_resource_id=f"rfi:other-{suffix}",
                        dependency_type="schedule_to_rfi",
                        metadata={"relation": "different"},
                    ),
                    expected_graph_revision=1,
                    idempotency_key=key,
                    actor_id="requester-1",
                    occurred_at=created_at,
                )

        loaded = store.get(tenant_id, project_id, resource_id)
        assert loaded is not None
        assert loaded.graph_revision == 1
        assert store.get(tenant_id, project_id, f"{resource_id}-other") is None
        assert len(store.history(tenant_id, project_id, resource_id)) == 1


def test_dependency_graph_live_concurrent_writes_serialize_on_project_revision() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"concurrent-tenant-{suffix}"
    project_id = f"concurrent-project-{suffix}"
    created_at = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    def make_link(name: str) -> DependencyLink:
        return DependencyLink(
            resource_id=f"dependency-{name}-{suffix}",
            tenant_id=tenant_id,
            project_id=project_id,
            revision=1,
            source_resource_id=f"schedule:{name}-{suffix}",
            target_resource_id=f"rfi:{name}-{suffix}",
            dependency_type="schedule_to_rfi",
            metadata={"relation": "blocks"},
        )

    with psycopg.connect(DSN) as setup:
        store = PostgresDependencyGraphStore(setup)
        store.initialize()
        store.ensure_project(tenant_id, project_id)
        setup.commit()

    first = psycopg.connect(DSN)
    second = psycopg.connect(DSN)
    second_started = threading.Event()
    second_done = threading.Event()
    second_result: list[object] = []

    def run_second() -> None:
        try:
            second.execute("BEGIN")
            second_started.set()
            stored = PostgresDependencyGraphStore(second).persist(
                make_link("second"),
                expected_graph_revision=0,
                idempotency_key=f"concurrent-second-{suffix}",
                actor_id="requester-2",
                occurred_at=created_at,
            )
            second.commit()
            second_result.append(stored)
        except Exception as exc:
            second.rollback()
            second_result.append(exc)
        finally:
            second_done.set()

    try:
        first.execute("BEGIN")
        PostgresDependencyGraphStore(first).persist(
            make_link("first"),
            expected_graph_revision=0,
            idempotency_key=f"concurrent-first-{suffix}",
            actor_id="requester-1",
            occurred_at=created_at,
        )

        worker = threading.Thread(target=run_second)
        worker.start()
        assert second_started.wait(timeout=5)
        assert not second_done.wait(timeout=0.2)

        first.rollback()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert len(second_result) == 1
        assert not isinstance(second_result[0], Exception)
        assert second_result[0].graph_revision == 1
        assert PostgresDependencyGraphStore(second).get(
            tenant_id, project_id, f"dependency-second-{suffix}"
        ) is not None
    finally:
        first.close()
        second.close()


def test_dependency_graph_live_concurrent_commit_allows_only_one_stale_writer() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"commit-race-tenant-{suffix}"
    project_id = f"commit-race-project-{suffix}"
    created_at = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    def make_link(name: str) -> DependencyLink:
        return DependencyLink(
            resource_id=f"dependency-{name}-{suffix}",
            tenant_id=tenant_id,
            project_id=project_id,
            revision=1,
            source_resource_id=f"schedule:{name}-{suffix}",
            target_resource_id=f"rfi:{name}-{suffix}",
            dependency_type="schedule_to_rfi",
            metadata={"relation": "blocks"},
        )

    with psycopg.connect(DSN) as setup:
        store = PostgresDependencyGraphStore(setup)
        store.initialize()
        store.ensure_project(tenant_id, project_id)
        setup.commit()

    first = psycopg.connect(DSN)
    second = psycopg.connect(DSN)
    second_started = threading.Event()
    second_done = threading.Event()
    second_result: list[object] = []

    def run_second() -> None:
        try:
            second.execute("BEGIN")
            second_started.set()
            try:
                second_result.append(
                    PostgresDependencyGraphStore(second).persist(
                        make_link("second"),
                        expected_graph_revision=0,
                        idempotency_key=f"commit-race-second-{suffix}",
                        actor_id="requester-2",
                        occurred_at=created_at,
                    )
                )
                second.commit()
            except Exception as exc:
                second.rollback()
                second_result.append(exc)
        finally:
            second_done.set()

    try:
        first.execute("BEGIN")
        first_result = PostgresDependencyGraphStore(first).persist(
            make_link("first"),
            expected_graph_revision=0,
            idempotency_key=f"commit-race-first-{suffix}",
            actor_id="requester-1",
            occurred_at=created_at,
        )
        assert first_result.graph_revision == 1

        worker = threading.Thread(target=run_second)
        worker.start()
        assert second_started.wait(timeout=5)
        assert not second_done.wait(timeout=0.2)

        first.commit()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert len(second_result) == 1
        assert isinstance(second_result[0], DependencyRevisionConflict)

        assert PostgresDependencyGraphStore(second).get(
            tenant_id, project_id, f"dependency-first-{suffix}"
        ) is not None
        assert PostgresDependencyGraphStore(second).get(
            tenant_id, project_id, f"dependency-second-{suffix}"
        ) is None
    finally:
        first.close()
        second.close()


def test_dependency_graph_live_resource_conflict_is_domain_error() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"resource-conflict-tenant-{suffix}"
    project_id = f"resource-conflict-project-{suffix}"
    resource_id = f"same-resource-{suffix}"
    created_at = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    link = DependencyLink(
        resource_id=resource_id,
        tenant_id=tenant_id,
        project_id=project_id,
        revision=1,
        source_resource_id=f"schedule:first-{suffix}",
        target_resource_id=f"rfi:first-{suffix}",
        dependency_type="schedule_to_rfi",
        metadata={"relation": "blocks"},
    )

    with psycopg.connect(DSN) as connection:
        store = PostgresDependencyGraphStore(connection)
        store.initialize()
        store.ensure_project(tenant_id, project_id)
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            store.persist(
                link,
                expected_graph_revision=0,
                idempotency_key=f"resource-first-{suffix}",
                actor_id="requester-1",
                occurred_at=created_at,
            )

        with PostgresTransactionManager(connection).transaction():
            with pytest.raises(DependencyResourceConflict, match="DEPENDENCY_RESOURCE_ALREADY_EXISTS"):
                store.persist(
                    DependencyLink(
                        resource_id=resource_id,
                        tenant_id=tenant_id,
                        project_id=project_id,
                        revision=1,
                        source_resource_id=f"schedule:second-{suffix}",
                        target_resource_id=f"rfi:second-{suffix}",
                        dependency_type="schedule_to_rfi",
                        metadata={"relation": "different"},
                    ),
                    expected_graph_revision=1,
                    idempotency_key=f"resource-second-{suffix}",
                    actor_id="requester-2",
                    occurred_at=created_at,
                )

        loaded = store.get(tenant_id, project_id, resource_id)
        assert loaded is not None
        assert loaded.graph_revision == 1
        assert len(store.history(tenant_id, project_id, resource_id)) == 1
