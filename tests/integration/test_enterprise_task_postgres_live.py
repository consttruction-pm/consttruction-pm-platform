from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from threading import Barrier
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import Permission
from construction_pm.enterprise_task_application import EnterpriseTaskApplicationService

from construction_pm.enterprise_task import (
    EnterpriseTask,
    EnterpriseTaskPriority,
    EnterpriseTaskStatus,
)
from construction_pm.enterprise_task_repository import (
    EnterpriseTaskDependencyError,
    EnterpriseTaskNotFound,
    PostgresEnterpriseTaskRepository,
)

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CONSTRUCTION_PM_POSTGRES_DSN is required")


def _task(task_id: str, tenant_id: str) -> EnterpriseTask:
    return EnterpriseTask(
        task_id=task_id,
        tenant_id=tenant_id,
        title=f"Task {task_id}",
        created_by_user_id="integration-user",
        created_at=datetime(2026, 11, 15, 9, 0, tzinfo=timezone.utc),
        priority=EnterpriseTaskPriority.NORMAL,
    )


def _new_scope() -> str:
    return f"enterprise-integration-{uuid.uuid4().hex}"


def test_postgres_task_round_trip_tenant_isolation_and_append_only_audit() -> None:
    psycopg = pytest.importorskip("psycopg")
    tenant = _new_scope()
    task_id = f"task-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        repository.initialize()
        created = repository.create(
            _task(task_id, tenant),
            idempotency_key="create-1",
            actor_id="integration-user",
            occurred_at=datetime(2026, 11, 15, 9, 1, tzinfo=timezone.utc),
        )
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        assert repository.get(tenant, task_id) == created
        with pytest.raises(EnterpriseTaskNotFound):
            repository.get(tenant + "-other", task_id)
        history = repository.history(tenant, task_id)
        assert [(event.revision, event.event_type) for event in history] == [(1, "created")]
        with pytest.raises(psycopg.Error, match="ENTERPRISE_TASK_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE enterprise_task_audit SET event_type='tampered' "
                "WHERE tenant_id=%s AND task_id=%s",
                (tenant, task_id),
            )
        connection.rollback()
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            connection.execute(
                "DELETE FROM enterprise_tasks WHERE tenant_id=%s AND task_id=%s",
                (tenant, task_id),
            )
        connection.rollback()
        assert repository.history(tenant, task_id) == history


def test_postgres_task_pagination_has_stable_composite_cursor_for_equal_timestamps() -> None:
    psycopg = pytest.importorskip("psycopg")
    tenant = _new_scope()
    timestamp = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        repository.initialize()
        for suffix in ("a", "b", "c"):
            item = repository.create(
                _task(f"task-{suffix}", tenant),
                idempotency_key=f"create-{suffix}",
                actor_id="integration-user",
                occurred_at=timestamp,
            )
            updated = replace(
                item.task,
                status=EnterpriseTaskStatus.IN_PROGRESS,
                updated_at=timestamp,
            )
            repository.update(
                updated,
                expected_revision=item.revision,
                actor_id="integration-user",
                occurred_at=timestamp,
            )
        for suffix in ("a", "b", "c"):
            repository.create(
                _task(f"null-{suffix}", tenant),
                idempotency_key=f"null-create-{suffix}",
                actor_id="integration-user",
                occurred_at=timestamp,
            )
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        first = repository.list_for_tenant(tenant, limit=2)
        assert [item.task.task_id for item in first] == ["task-a", "task-b"]
        last = first[-1].task
        second = repository.list_for_tenant(
            tenant, limit=2, before_updated_at=last.updated_at, before_task_id=last.task_id
        )
        assert [item.task.task_id for item in second] == ["task-c", "null-a"]
        assert len({item.task.task_id for item in first + second}) == 4
        null_page = repository.list_for_tenant(
            tenant, limit=2, before_updated_at=None, before_task_id="null-a"
        )
        assert [item.task.task_id for item in null_page] == ["null-b", "null-c"]


def test_postgres_completion_actor_must_match_authenticated_operation_actor() -> None:
    psycopg = pytest.importorskip("psycopg")
    tenant = _new_scope()
    task_id = f"complete-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        repository.initialize()
        created = repository.create(
            _task(task_id, tenant),
            idempotency_key="completion-create",
            actor_id="integration-user",
            occurred_at=datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc),
        )
        completed = replace(
            created.task,
            status=EnterpriseTaskStatus.COMPLETED,
            completed_at=datetime(2026, 11, 15, 12, 1, tzinfo=timezone.utc),
            completed_by_user_id="different-user",
        )
        with pytest.raises(ValueError, match="ENTERPRISE_TASK_COMPLETION_ACTOR_MISMATCH"):
            repository.update(
                completed,
                expected_revision=created.revision,
                actor_id="integration-user",
                occurred_at=datetime(2026, 11, 15, 12, 1, tzinfo=timezone.utc),
            )
        connection.rollback()


def test_postgres_dependency_cycle_check_serializes_concurrent_graph_mutations() -> None:
    psycopg = pytest.importorskip("psycopg")
    tenant = _new_scope()
    task_a, task_b = f"a-{uuid.uuid4().hex}", f"b-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        repository.initialize()
        for task_id in (task_a, task_b):
            repository.create(
                _task(task_id, tenant), idempotency_key=f"create-{task_id}",
                actor_id="integration-user",
                occurred_at=datetime(2026, 11, 15, 11, 0, tzinfo=timezone.utc),
            )
        connection.commit()

    barrier = Barrier(2)

    def add_edge(source_id: str, target_id: str) -> str:
        with psycopg.connect(DSN) as connection:
            repository = PostgresEnterpriseTaskRepository(connection)
            current = repository.get(tenant, source_id)
            barrier.wait(timeout=10)
            changed = replace(current.task, dependency_ids=(target_id,))
            try:
                repository.update(
                    changed,
                    expected_revision=current.revision,
                    actor_id="integration-user",
                    occurred_at=datetime(2026, 11, 15, 11, 1, tzinfo=timezone.utc),
                )
            except EnterpriseTaskDependencyError:
                return "cycle-rejected"
            return "saved"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(add_edge, task_a, task_b), executor.submit(add_edge, task_b, task_a)]
        results = sorted(future.result(timeout=25) for future in futures)
    assert results == ["cycle-rejected", "saved"]
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        persisted = [repository.get(tenant, task_id).task for task_id in (task_a, task_b)]
        assert sum(bool(item.dependency_ids) for item in persisted) == 1


def test_postgres_create_idempotency_ignores_generated_task_id_and_timestamp() -> None:
    psycopg = pytest.importorskip("psycopg")
    tenant = _new_scope()
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        repository.initialize()
        first = repository.create(
            _task("generated-first", tenant),
            idempotency_key="same-request",
            actor_id="integration-user",
            occurred_at=datetime(2026, 11, 15, 13, 1, tzinfo=timezone.utc),
        )
        retry_task = replace(
            _task("generated-retry", tenant),
            title="Task generated-first",
            created_at=datetime(2026, 11, 15, 13, 2, tzinfo=timezone.utc),
        )
        retried = repository.create(
            retry_task,
            idempotency_key="same-request",
            actor_id="integration-user",
            occurred_at=datetime(2026, 11, 15, 13, 3, tzinfo=timezone.utc),
        )
        connection.commit()
    assert retried == first


def test_postgres_task_listing_filters_project_and_personal_scopes() -> None:
    psycopg = pytest.importorskip("psycopg")
    tenant = _new_scope()
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        repository.initialize()
        tasks = [
            replace(_task("project-a", tenant), project_id="project-a"),
            replace(_task("project-b", tenant), project_id="project-b"),
            _task("personal-a", tenant),
        ]
        for index, task in enumerate(tasks):
            repository.create(
                task,
                idempotency_key=f"filter-{index}",
                actor_id="integration-user",
                occurred_at=datetime(2026, 11, 15, 14, 1, tzinfo=timezone.utc),
            )
        connection.commit()
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        project_items = repository.list_for_tenant(tenant, project_id="project-a")
        personal_items = repository.list_for_tenant(tenant, personal_user_id="integration-user")
    assert [item.task.task_id for item in project_items] == ["project-a"]
    assert [item.task.task_id for item in personal_items] == ["personal-a"]


def test_postgres_authenticated_task_application_personal_and_project_vertical_slice() -> None:
    psycopg = pytest.importorskip("psycopg")
    tenant = _new_scope()
    now = datetime(2026, 11, 15, 15, 0, tzinfo=timezone.utc)

    class Lifecycle:
        def get_session(self, session_id, *, now):
            assert session_id == "session-a"
            return SimpleNamespace(user_id="integration-user", tenant_id=tenant, roles=frozenset({"project_manager", "enterprise_user"}))

        def authorize_project(self, session_id, project_id, permission, *, now):
            assert session_id == "session-a"
            assert permission in {Permission.PROJECT_READ, Permission.PROJECT_WRITE}
            return SimpleNamespace(context=SimpleNamespace(tenant_id=tenant, project_id=project_id))

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        repository.initialize()
        service = EnterpriseTaskApplicationService(repository, Lifecycle(), clock=lambda: now)
        personal = service.create_task(
            "session-a",
            {"title": "Personal follow-up"},
            idempotency_key="personal-vertical-slice",
        )
        project = service.create_task(
            "session-a",
            {"title": "Project action", "project_id": "project-v1"},
            idempotency_key="project-vertical-slice",
        )
        assert [item.task.task_id for item in service.list_tasks("session-a")] == [personal.task.task_id]
        assert [item.task.task_id for item in service.list_tasks("session-a", project_id="project-v1")] == [project.task.task_id]
        updated = service.update_task(
            "session-a",
            personal.task.task_id,
            {"expected_revision": 1, "status": "completed"},
        )
        assert updated.task.completed_by_user_id == "integration-user"
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseTaskRepository(connection)
        persisted = repository.get(tenant, personal.task.task_id)
        assert persisted.revision == 2
        assert persisted.task.status is EnterpriseTaskStatus.COMPLETED
