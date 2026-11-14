import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from construction_pm.postgres_project_lifecycle import PostgresProjectRepository
from construction_pm.p6_obs_repository import (
    P6OBSApplicationService,
    P6OBSNode,
    PostgresP6OBSRepository,
)

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
        "DELETE FROM project_lifecycle_defaults_event WHERE tenant_id=%s", (tenant,)
    )
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


def test_postgres_activity_defaults_round_trip_and_partial_update():
    tenant, user, project = "tenant-defaults-live", "user-defaults-live", "project-defaults-live"
    with connect() as connection:
        _prepare(connection, tenant)
        repo = PostgresProjectRepository(connection)
        created = repo.create_for_user(
            tenant,
            user,
            project,
            "Defaults Live",
            default_activity_type="Resource Dependent",
            default_percent_complete_type="PHYSICAL",
            activity_id_prefix="AH-",
            activity_id_suffix="-B",
            activity_id_increment=25,
            increment_activity_id=True,
        )
        connection.commit()
        assert created.default_activity_type == "Resource Dependent"
        assert created.default_percent_complete_type == "PHYSICAL"
        assert created.activity_id_prefix == "AH-"
        assert created.activity_id_suffix == "-B"
        assert created.activity_id_increment == 25
        assert created.increment_activity_id is True

        read_back = repo.get_for_user(tenant, project, user)
        assert read_back is not None
        assert read_back.default_activity_type == "Resource Dependent"
        assert read_back.default_percent_complete_type == "PHYSICAL"
        assert read_back.activity_id_prefix == "AH-"
        assert read_back.activity_id_suffix == "-B"
        assert read_back.activity_id_increment == 25
        assert read_back.increment_activity_id is True

        updated = repo.update_for_user(
            tenant,
            user,
            project,
            expected_revision=0,
            name="Defaults Live",
            activity_id_increment=5,
        )
        connection.commit()
        assert updated is not None
        assert updated.activity_id_increment == 5
        assert updated.default_activity_type == "Resource Dependent"
        assert updated.increment_activity_id is True

        cleared = repo.update_for_user(
            tenant,
            user,
            project,
            expected_revision=1,
            name="Defaults Live",
            activity_id_prefix="",
            increment_activity_id=False,
        )
        connection.commit()
        assert cleared is not None
        assert cleared.activity_id_prefix == ""
        assert cleared.increment_activity_id is False
        assert cleared.default_percent_complete_type == "PHYSICAL"


def test_postgres_defaults_application_history_is_append_only_and_scoped():
    tenant, user, project = (
        "tenant-defaults-history-live",
        "user-defaults-history-live",
        "project-defaults-history-live",
    )
    now = datetime(2026, 11, 14, 10, 15, tzinfo=timezone.utc)
    with connect() as connection:
        _prepare(connection, tenant)
        repo = PostgresProjectRepository(connection)
        repo.create_for_user(tenant, user, project, "Defaults History Live")
        connection.commit()

        event = repo.record_defaults_application_for_user(
            tenant,
            user,
            project,
            activity_id="A1000",
            applied_activity_type="Level of Effort",
            applied_percent_complete_type="PHYSICAL",
            applied_duration_type="Fixed Units",
            applied_cost_account_id="CA-CIVIL",
            actor_user_id=user,
            recorded_at=now,
        )
        connection.commit()
        assert event.event_id == f"{project}@A1000"
        assert event.applied_cost_account_id == "CA-CIVIL"
        assert event.recorded_at == now

        # A retried write keeps the first row: the history is append-only.
        replay = repo.record_defaults_application_for_user(
            tenant,
            user,
            project,
            activity_id="A1000",
            applied_activity_type="Changed",
            applied_percent_complete_type="",
            applied_duration_type="",
            applied_cost_account_id="",
            actor_user_id=user,
            recorded_at=now,
        )
        connection.commit()
        assert replay.applied_activity_type == "Level of Effort"
        history = repo.defaults_history_for_user(tenant, project, user)
        assert [item.event_id for item in history] == [f"{project}@A1000"]

        # Another tenant and a non-member cannot read the row.
        assert repo.defaults_history_for_user("tenant-other", project, user) == ()
        assert repo.defaults_history_for_user(tenant, project, "user-other") == ()


def test_postgres_responsibility_structure_and_project_assignment_round_trip():
    tenant, user, project = (
        "tenant-obs-live",
        "user-obs-live",
        "project-obs-live",
    )
    with connect() as connection:
        _prepare(connection, tenant)
        obs_repository = PostgresP6OBSRepository(connection)
        obs_repository.initialize()
        connection.execute(
            "DELETE FROM p6_obs_node WHERE tenant_id=%s", (tenant,)
        )
        connection.commit()

        service = P6OBSApplicationService(obs_repository)
        service.save(
            P6OBSNode(tenant, "OBS-ROOT", None, "ROOT", "Company", sequence_number=1)
        )
        service.save(
            P6OBSNode(tenant, "OBS-CIVIL", "OBS-ROOT", "CIV", "Civil")
        )
        connection.commit()

        assert obs_repository.obs_node_exists(tenant, "OBS-CIVIL") is True
        assert obs_repository.obs_node_exists("tenant-other", "OBS-CIVIL") is False
        assert [item.obs_id for item in obs_repository.list(tenant)] == [
            "OBS-CIVIL",
            "OBS-ROOT",
        ]

        repo = PostgresProjectRepository(connection)
        created = repo.create_for_user(
            tenant, user, project, "OBS Live", obs_id="OBS-CIVIL"
        )
        connection.commit()
        assert created.obs_id == "OBS-CIVIL"

        read_back = repo.get_for_user(tenant, project, user)
        assert read_back is not None and read_back.obs_id == "OBS-CIVIL"

        moved = repo.update_for_user(
            tenant,
            user,
            project,
            expected_revision=0,
            name="OBS Live",
            obs_id="OBS-ROOT",
        )
        connection.commit()
        assert moved is not None and moved.obs_id == "OBS-ROOT"

        cleared = repo.update_for_user(
            tenant,
            user,
            project,
            expected_revision=1,
            name="OBS Live",
            obs_id="",
        )
        connection.commit()
        assert cleared is not None and cleared.obs_id == ""


def test_postgres_lifecycle_schema_initialization_executes_every_statement():
    """Every Python schema statement must execute; the deployed runtime uses them.

    The infra SQL file is exercised by the tests above, but production boot uses
    ``initialize_project_lifecycle_schema`` directly, so a malformed statement
    would only surface at deployment time.
    """

    from construction_pm.postgres_project_lifecycle import (
        initialize_project_lifecycle_schema,
    )

    with connect() as connection:
        initialize_project_lifecycle_schema(connection)
        columns = {
            row[0]
            for row in connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='project_lifecycle_projects'"
            ).fetchall()
        }
        connection.commit()

    assert {
        "default_duration_type",
        "default_cost_account_id",
        "obs_id",
        "checkout_state",
        "checked_out_by",
    } <= columns
