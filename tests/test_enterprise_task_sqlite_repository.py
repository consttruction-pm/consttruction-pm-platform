from __future__ import annotations

import sqlite3
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from construction_pm.enterprise_task import (
    EnterpriseTask,
    EnterpriseTaskPriority,
    EnterpriseTaskStatus,
)
from construction_pm.enterprise_task_repository import (
    EnterpriseTaskDependencyError,
    EnterpriseTaskIdempotencyReuse,
    EnterpriseTaskNotFound,
    EnterpriseTaskRevisionConflict,
)
from construction_pm.enterprise_task_sqlite_repository import SQLiteEnterpriseTaskRepository

CREATED = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
LATER = CREATED + timedelta(minutes=5)
LATER2 = CREATED + timedelta(minutes=10)


def _task(task_id: str, *, tenant="tenant-a", title="Task", deps=(), project_id=None, created_by="alice"):
    return EnterpriseTask(
        task_id=task_id,
        tenant_id=tenant,
        title=title,
        created_by_user_id=created_by,
        created_at=CREATED,
        status=EnterpriseTaskStatus.OPEN,
        priority=EnterpriseTaskPriority.NORMAL,
        project_id=project_id,
        dependency_ids=tuple(deps),
    )


class SQLiteEnterpriseTaskRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.repository = SQLiteEnterpriseTaskRepository(self.connection)
        self.repository.initialize()

    def tearDown(self):
        self.connection.close()

    def _create(self, task_id, *, key=None, **kwargs):
        return self.repository.create(
            _task(task_id, **kwargs),
            idempotency_key=key or f"key-{task_id}",
            actor_id=kwargs.get("created_by", "alice"),
            occurred_at=LATER,
        )

    def test_create_persists_revision_and_history(self):
        stored = self._create("task-1", title="First")
        self.assertEqual(stored.revision, 1)
        self.assertEqual(stored.task.revision, 1)
        self.assertEqual(self.repository.get("tenant-a", "task-1").task.title, "First")

        history = self.repository.history("tenant-a", "task-1")
        self.assertEqual([(event.revision, event.event_type) for event in history], [(1, "created")])
        self.assertEqual(history[0].actor_id, "alice")

    def test_create_is_idempotent_and_rejects_key_reuse_with_different_payload(self):
        first = self._create("task-1", key="same-key", title="First")
        second = self.repository.create(
            _task("task-1", title="First"),
            idempotency_key="same-key",
            actor_id="alice",
            occurred_at=LATER2,
        )
        self.assertEqual(second.revision, first.revision)
        self.assertEqual(second.task.title, "First")
        self.assertEqual(len(self.repository.list_for_tenant("tenant-a")), 1)

        with self.assertRaises(EnterpriseTaskIdempotencyReuse):
            self.repository.create(
                _task("task-2", title="Different"),
                idempotency_key="same-key",
                actor_id="alice",
                occurred_at=LATER,
            )

    def test_get_and_list_are_tenant_scoped(self):
        self._create("task-1")
        self._create("task-2", tenant="tenant-b", created_by="carol")

        self.assertEqual(len(self.repository.list_for_tenant("tenant-a")), 1)
        self.assertEqual(len(self.repository.list_for_tenant("tenant-b")), 1)
        with self.assertRaises(EnterpriseTaskNotFound):
            self.repository.get("tenant-b", "task-1")
        # A history query for the wrong tenant yields nothing rather than leaking rows.
        self.assertEqual(self.repository.history("tenant-b", "task-1"), ())

    def test_list_filters_by_project_and_personal_scope(self):
        self._create("task-personal")
        self._create("task-project", project_id="project-1")
        self._create("task-other-user", created_by="bob")
        self.repository.create(
            _task("task-assigned", created_by="bob", deps=()),
            idempotency_key="key-assigned",
            actor_id="bob",
            occurred_at=LATER,
        )

        personal = self.repository.list_for_tenant("tenant-a", personal_user_id="alice")
        self.assertEqual({item.task.task_id for item in personal}, {"task-personal"})

        project = self.repository.list_for_tenant("tenant-a", project_id="project-1")
        self.assertEqual([item.task.task_id for item in project], ["task-project"])

        with self.assertRaises(ValueError):
            self.repository.list_for_tenant("tenant-a", project_id="p", personal_user_id="alice")

    def test_update_increments_revision_and_appends_history(self):
        stored = self._create("task-1")
        updated = self.repository.update(
            replace(stored.task, title="Renamed"),
            expected_revision=1,
            actor_id="alice",
            occurred_at=LATER2,
        )
        self.assertEqual(updated.revision, 2)
        self.assertEqual(updated.task.title, "Renamed")
        self.assertEqual(updated.task.updated_at, LATER2)
        self.assertEqual(
            [(event.revision, event.event_type) for event in self.repository.history("tenant-a", "task-1")],
            [(1, "created"), (2, "updated")],
        )

    def test_stale_update_is_rejected(self):
        stored = self._create("task-1")
        self.repository.update(
            replace(stored.task, title="Renamed"),
            expected_revision=1,
            actor_id="alice",
            occurred_at=LATER2,
        )
        with self.assertRaises(EnterpriseTaskRevisionConflict):
            self.repository.update(
                replace(stored.task, title="Stale"),
                expected_revision=1,
                actor_id="alice",
                occurred_at=LATER2,
            )

    def test_completion_requires_the_acting_user(self):
        stored = self._create("task-1")
        completed = replace(
            stored.task,
            status=EnterpriseTaskStatus.COMPLETED,
            completed_at=LATER2,
            completed_by_user_id="alice",
        )
        updated = self.repository.update(
            completed, expected_revision=1, actor_id="alice", occurred_at=LATER2
        )
        self.assertEqual(updated.task.status, EnterpriseTaskStatus.COMPLETED)
        self.assertEqual(self.repository.history("tenant-a", "task-1")[-1].event_type, "completed")

        # A second task completed by a different actor is refused.
        other = self._create("task-2")
        with self.assertRaises(ValueError):
            self.repository.update(
                replace(
                    other.task,
                    status=EnterpriseTaskStatus.COMPLETED,
                    completed_at=LATER2,
                    completed_by_user_id="bob",
                ),
                expected_revision=1,
                actor_id="alice",
                occurred_at=LATER2,
            )

    def test_dependency_cycle_is_rejected(self):
        self._create("task-a")
        self._create("task-b")
        self.repository.update(
            replace(self.repository.get("tenant-a", "task-a").task, dependency_ids=("task-b",)),
            expected_revision=1,
            actor_id="alice",
            occurred_at=LATER2,
        )
        with self.assertRaises(EnterpriseTaskDependencyError):
            self.repository.update(
                replace(self.repository.get("tenant-a", "task-b").task, dependency_ids=("task-a",)),
                expected_revision=1,
                actor_id="alice",
                occurred_at=LATER2,
            )

    def test_dependency_outside_tenant_is_rejected(self):
        self._create("task-other", tenant="tenant-b", created_by="carol")
        with self.assertRaises(EnterpriseTaskDependencyError):
            self._create("task-a", deps=("task-other",))

    def test_metadata_validation(self):
        with self.assertRaises(ValueError):
            self.repository.create(
                _task("task-1"),
                idempotency_key="",
                actor_id="alice",
                occurred_at=LATER,
            )
        with self.assertRaises(ValueError):
            self.repository.create(
                _task("task-1"),
                idempotency_key="key",
                actor_id="alice",
                occurred_at=datetime(2026, 11, 15, 12, 0),
            )
        with self.assertRaises(ValueError):
            self.repository.get("", "task-1")

    def test_pagination_cursor_is_tenant_scoped(self):
        self._create("task-1")
        self._create("task-2")
        self._create("task-3")
        first_page = self.repository.list_for_tenant("tenant-a", limit=2)
        self.assertEqual(len(first_page), 2)
        cursor = first_page[-1]
        rest = self.repository.list_for_tenant(
            "tenant-a",
            limit=2,
            before_updated_at=cursor.task.updated_at,
            before_task_id=cursor.task.task_id,
        )
        self.assertEqual(len(rest), 1)
        self.assertNotIn(rest[0].task.task_id, {item.task.task_id for item in first_page})


if __name__ == "__main__":
    unittest.main()
