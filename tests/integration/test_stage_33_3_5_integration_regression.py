from __future__ import annotations

from dataclasses import dataclass

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    default_project_policy,
)
from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.server_idempotency import (
    IdempotencyRecord,
    mutation_fingerprint,
)
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome
from shared.client.client_context import ProjectContext


@dataclass
class _Tx:
    active: bool = False

    def transaction(self):
        outer = self

        class _Context:
            def __enter__(self):
                outer.active = True
                return outer

            def __exit__(self, exc_type, exc, tb):
                outer.active = False
                return False

        return _Context()


class _Persistence:
    def __init__(self):
        self.records: dict[tuple[str, str, str], IdempotencyRecord] = {}

    def lock_idempotency(self, tenant_id, project_id, key):
        pass

    def get_idempotency(self, tenant_id, project_id, key):
        return self.records.get((tenant_id, project_id, key))

    def put_idempotency(self, record):
        self.records[(record.tenant_id, record.project_id, record.idempotency_key)] = record


class _Delegate:
    def __init__(self):
        self.calls = 0

    def submit(self, mutation):
        self.calls += 1
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def _mutation(revision: int = 4) -> OfflineMutation:
    return OfflineMutation(
        mutation_id="mutation-1",
        tenant_id="tenant-1",
        project_id="project-1",
        expected_revision=revision,
        operation="update_activity",
        payload={"activity_id": "A-1", "name": "Foundation"},
        idempotency_key="idem-1",
    )


def test_application_context_authorization_and_sync_share_same_project_boundary() -> None:
    context = ProjectContext("tenant-1", "project-1", 4)
    auth = default_project_policy()
    auth_context = AuthorizationContext(
        context.tenant_id,
        context.project_id,
        "user-1",
        frozenset({"planner"}),
    )
    auth.require(auth_context, Permission.PROJECT_SCHEDULE)

    persistence = _Persistence()
    delegate = _Delegate()
    executor = AtomicSyncExecutor(persistence, _Tx(), delegate)

    first = executor.submit(_mutation(context.revision))
    replay = executor.submit(_mutation(context.revision))

    assert first.disposition is SyncDisposition.ACKNOWLEDGED
    assert replay.disposition is SyncDisposition.ACKNOWLEDGED
    assert delegate.calls == 1
    assert len(persistence.records) == 1


def test_denied_authorization_does_not_enter_sync_boundary() -> None:
    context = ProjectContext("tenant-1", "project-1", 4)
    auth = default_project_policy()
    auth_context = AuthorizationContext(
        context.tenant_id,
        context.project_id,
        "user-1",
        frozenset({"viewer"}),
    )
    with pytest.raises(AuthorizationError):
        auth.require(auth_context, Permission.PROJECT_SCHEDULE)

    delegate = _Delegate()
    assert delegate.calls == 0


def test_stale_revision_identity_is_preserved_in_mutation_fingerprint() -> None:
    first = _mutation(4)
    changed = _mutation(5)

    assert mutation_fingerprint(first) != mutation_fingerprint(changed)
