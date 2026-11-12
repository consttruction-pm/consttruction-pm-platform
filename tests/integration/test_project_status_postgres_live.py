import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from construction_pm.postgres_project_lifecycle import PostgresProjectRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

SCHEMA = Path(__file__).resolve().parents[2] / "infra" / "project_lifecycle_schema.sql"


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def _prepare(connection, tenant: str) -> None:
    connection.execute(SCHEMA.read_text())
    connection.execute(
        "DELETE FROM project_lifecycle_status_event WHERE tenant_id=%s", (tenant,)
    )
    connection.execute(
        "DELETE FROM project_lifecycle_memberships WHERE tenant_id=%s", (tenant,)
    )
    connection.execute(
        "DELETE FROM project_lifecycle_projects WHERE tenant_id=%s", (tenant,)
    )
    connection.commit()


def test_postgres_status_change_is_audited_and_idempotent():
    tenant, user, project = "tenant-status-live", "user-status-live", "project-status-live"
    now = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)
    with connect() as connection:
        _prepare(connection, tenant)
        repo = PostgresProjectRepository(connection)
        created = repo.create_for_user(tenant, user, project, "Status Live")
        connection.commit()
        assert created.status == "active"

        updated = repo.set_status_for_user(
            tenant,
            user,
            project,
            status="what_if",
            expected_revision=0,
            actor_user_id=user,
            recorded_at=now,
        )
        connection.commit()
        assert updated is not None
        assert updated.status == "what_if" and updated.settings_revision == 1

        history = repo.status_history_for_user(tenant, project, user)
        assert len(history) == 1
        assert history[0].event_id == f"{project}@1"
        assert history[0].from_status == "active" and history[0].to_status == "what_if"
        assert history[0].actor_user_id == user
        assert history[0].recorded_at == now

        # Same target status is a no-op: no revision bump and no duplicate event,
        # even when the caller retries with the pre-change token.
        replay = repo.set_status_for_user(
            tenant,
            user,
            project,
            status="what_if",
            expected_revision=0,
            actor_user_id=user,
            recorded_at=now,
        )
        connection.commit()
        assert replay is not None
        assert replay.status == "what_if" and replay.settings_revision == 1
        assert repo.status_history_for_user(tenant, project, user) == history

        assert (
            repo.set_status_for_user(
                tenant,
                user,
                project,
                status="inactive",
                expected_revision=0,
                actor_user_id=user,
                recorded_at=now,
            )
            is None
        )
        assert repo.status_history_for_user("tenant-other", project, user) == ()
