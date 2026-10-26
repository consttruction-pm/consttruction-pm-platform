"""PostgreSQL twin coverage for append-only layout revision history."""

import os
import uuid

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn,
    PersistedP6Layout,
    P6LayoutPersistenceError,
    PostgresP6LayoutRepository,
)


pytestmark = pytest.mark.postgres


def _connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(dsn)


def _layout(revision: int, width: int, tenant: str, project: str = "layout-pg") -> PersistedP6Layout:
    return PersistedP6Layout(
        BackendScope(tenant, project, 7),
        "project",
        "activity",
        revision,
        (LayoutColumn("activity_id", True, 0, None, width, "start", False, False),),
        {"future": {"enabled": True}},
    )


def test_postgres_layout_revision_history_is_newest_first_and_scoped():
    tenant = f"tenant-layout-{uuid.uuid4()}"
    with _connection() as connection:
        repo = PostgresP6LayoutRepository(connection)
        repo.initialize()
        try:
            repo.upsert(_layout(1, 120, tenant))
            repo.upsert(_layout(2, 180, tenant))
            repo.upsert(_layout(3, 240, tenant))

            revisions = repo.list_revisions(
                BackendScope(tenant, "layout-pg", 7), "project", "activity"
            )
            assert [item.revision for item in revisions] == [3, 2, 1]
            assert [item.columns[0].width for item in revisions] == [240, 180, 120]
            assert revisions[0].metadata == {"future": {"enabled": True}}

            limited = repo.list_revisions(
                BackendScope(tenant, "layout-pg", 7), "project", "activity", limit=2
            )
            assert [item.revision for item in limited] == [3, 2]

            assert repo.list_revisions(
                BackendScope(tenant, "layout-pg", 8), "project", "activity"
            ) == ()
            assert repo.list_revisions(
                BackendScope(tenant, "layout-pg", 7), "user", "activity"
            ) == ()
            assert repo.list_revisions(
                BackendScope(tenant, "other-project", 7), "project", "activity"
            ) == ()
            assert repo.list_revisions(
                BackendScope("other-tenant", "layout-pg", 7), "project", "activity"
            ) == ()

            with pytest.raises(P6LayoutPersistenceError, match="INVALID_LAYOUT_HISTORY_LIMIT"):
                repo.list_revisions(
                    BackendScope(tenant, "layout-pg", 7), "project", "activity", limit=0
                )
            with pytest.raises(P6LayoutPersistenceError, match="INVALID_LAYOUT_HISTORY_LIMIT"):
                repo.list_revisions(
                    BackendScope(tenant, "layout-pg", 7), "project", "activity", limit=101
                )

            # Retrying the stored head is idempotent and appends nothing.
            assert repo.upsert(_layout(3, 240, tenant)) == _layout(3, 240, tenant)
            assert [item.revision for item in repo.list_revisions(
                BackendScope(tenant, "layout-pg", 7), "project", "activity"
            )] == [3, 2, 1]

            # Stale bases conflict; rewriting a published revision is immutable.
            with pytest.raises(P6LayoutPersistenceError, match="REVISION_CONFLICT"):
                repo.upsert(_layout(2, 300, tenant))
            with pytest.raises(P6LayoutPersistenceError, match="IMMUTABLE_LAYOUT_REVISION"):
                repo.upsert(_layout(3, 999, tenant))
            with pytest.raises(P6LayoutPersistenceError, match="REVISION_CONFLICT"):
                repo.upsert(_layout(5, 240, tenant))
            assert [item.revision for item in repo.list_revisions(
                BackendScope(tenant, "layout-pg", 7), "project", "activity"
            )] == [3, 2, 1]
        finally:
            connection.rollback()
