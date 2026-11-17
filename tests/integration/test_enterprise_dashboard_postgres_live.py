from __future__ import annotations

import os
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from construction_pm.enterprise_dashboard import (
    DashboardFilter,
    DashboardLayout,
    DashboardPortlet,
    EnterpriseDashboard,
    EnterpriseDashboardError,
    EnterpriseDashboardNotFound,
    EnterpriseDashboardRevisionConflict,
    PORTFOLIO_CONTROL_SNAPSHOT,
)
from construction_pm.enterprise_dashboard_repository import (
    PostgresEnterpriseDashboardRepository,
)

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") or os.getenv("P6_TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="CONSTRUCTION_PM_POSTGRES_DSN or P6_TEST_POSTGRES_DSN is required")

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def new_scope() -> str:
    return f"ent-dashboard-{uuid.uuid4().hex}"


def make_dashboard(
    tenant_id: str,
    dashboard_id: str,
    *,
    created_at=NOW,
    title="Integration dashboard",
) -> EnterpriseDashboard:
    portlet = DashboardPortlet(
        instance_id="portlet-1",
        type_id=PORTFOLIO_CONTROL_SNAPSHOT,
        contract_version=PORTFOLIO_CONTROL_SNAPSHOT,
        config={"portfolio_id": "portfolio-1"},
        layout=DashboardLayout(0, 0, 6, 4),
    )
    return EnterpriseDashboard(
        dashboard_id=dashboard_id,
        tenant_id=tenant_id,
        context="enterprise_home",
        context_portfolio_id=None,
        owner_user_id="integration-owner",
        title=title,
        description="PostgreSQL persistence test",
        status="active",
        visibility="private",
        shared_user_ids=(),
        shared_role_ids=(),
        portlets=(portlet,),
        filters=(DashboardFilter("membership_status", "eq", "included"),),
        revision=1,
        created_at=created_at,
    )


def test_postgres_dashboard_round_trip_revision_sharing_tenant_isolation_and_append_only_audit():
    psycopg = pytest.importorskip("psycopg")
    tenant = new_scope()
    dashboard_id = f"dashboard-{uuid.uuid4().hex}"

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        repository.initialize()
        created = repository.create(
            make_dashboard(tenant, dashboard_id),
            idempotency_key="create-1",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        assert created.revision == 1

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        assert repository.get(tenant, dashboard_id) == created
        with pytest.raises(EnterpriseDashboardNotFound):
            repository.get(tenant + "-other", dashboard_id)

        shared = replace(
            created.dashboard,
            shared_user_ids=("integration-viewer",),
            visibility="users",
        )
        updated = repository.update(
            shared,
            expected_revision=1,
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(minutes=1),
            event_type="shared",
        )
        assert updated.revision == 2
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        persisted = repository.get(tenant, dashboard_id)
        assert persisted.revision == 2
        assert persisted.dashboard.shared_user_ids == ("integration-viewer",)
        history = repository.history(tenant, dashboard_id)
        assert [(item.revision, item.event_type) for item in history] == [
            (1, "created"),
            (2, "shared"),
        ]

        with pytest.raises(EnterpriseDashboardRevisionConflict):
            repository.update(
                replace(persisted.dashboard, title="Conflicting stale payload"),
                expected_revision=1,
                actor_id="integration-owner",
                occurred_at=NOW + timedelta(minutes=2),
            )
        connection.rollback()

        with pytest.raises(psycopg.Error, match="ENTERPRISE_DASHBOARD_AUDIT_APPEND_ONLY"):
            connection.execute(
                "UPDATE enterprise_dashboard_audit SET event_type='tampered' "
                "WHERE tenant_id=%s AND dashboard_id=%s",
                (tenant, dashboard_id),
            )
        connection.rollback()

        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            connection.execute(
                "DELETE FROM enterprise_dashboards WHERE tenant_id=%s AND dashboard_id=%s",
                (tenant, dashboard_id),
            )
        connection.rollback()
        assert repository.history(tenant, dashboard_id) == history


def test_postgres_dashboard_titles_are_unique_case_insensitively_within_tenant():
    psycopg = pytest.importorskip("psycopg")
    tenant = new_scope()
    first_id = f"dashboard-{uuid.uuid4().hex}"
    second_id = f"dashboard-{uuid.uuid4().hex}"

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        repository.initialize()
        first = repository.create(
            make_dashboard(tenant, first_id, title="Executive Overview"),
            idempotency_key="unique-title-first",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        second = repository.create(
            make_dashboard(tenant, second_id, title="Portfolio Metrics"),
            idempotency_key="unique-title-second",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=2),
        )
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        with pytest.raises(EnterpriseDashboardError, match="TITLE_ALREADY_EXISTS"):
            repository.create(
                make_dashboard(
                    tenant,
                    f"dashboard-{uuid.uuid4().hex}",
                    title=" executive overview ",
                ),
                idempotency_key="unique-title-third",
                actor_id="integration-owner",
                occurred_at=NOW + timedelta(seconds=3),
            )
        connection.rollback()

        with pytest.raises(EnterpriseDashboardError, match="TITLE_ALREADY_EXISTS"):
            repository.update(
                replace(second.dashboard, title="EXECUTIVE OVERVIEW"),
                expected_revision=1,
                actor_id="integration-owner",
                occurred_at=NOW + timedelta(minutes=1),
            )
        connection.rollback()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        assert repository.get(tenant, first_id).dashboard.title == "Executive Overview"
        assert repository.get(tenant, second_id).dashboard.title == "Portfolio Metrics"


def test_postgres_dashboard_idempotency_returns_original_and_rejects_payload_reuse():
    psycopg = pytest.importorskip("psycopg")
    tenant = new_scope()
    first_id = f"dashboard-{uuid.uuid4().hex}"
    retry_id = f"dashboard-{uuid.uuid4().hex}"

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        repository.initialize()
        first = repository.create(
            make_dashboard(tenant, first_id),
            idempotency_key="same-request",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        retry = repository.create(
            make_dashboard(
                tenant,
                retry_id,
                created_at=NOW + timedelta(minutes=3),
            ),
            idempotency_key="same-request",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(minutes=3, seconds=1),
        )
        assert retry == first
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        changed = replace(make_dashboard(tenant, f"dashboard-{uuid.uuid4().hex}"), title="Different payload")
        with pytest.raises(ValueError, match="IDEMPOTENCY_KEY_REUSE"):
            repository.create(
                changed,
                idempotency_key="same-request",
                actor_id="integration-owner",
                occurred_at=NOW + timedelta(minutes=4),
            )
        connection.rollback()


def test_postgres_dashboard_create_and_audit_are_atomic_on_rollback():
    psycopg = pytest.importorskip("psycopg")
    tenant = new_scope()
    dashboard_id = f"dashboard-{uuid.uuid4().hex}"

    with psycopg.connect(DSN) as setup_connection:
        PostgresEnterpriseDashboardRepository(setup_connection).initialize()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        repository.create(
            make_dashboard(tenant, dashboard_id),
            idempotency_key="rollback-create",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        connection.rollback()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        with pytest.raises(EnterpriseDashboardNotFound):
            repository.get(tenant, dashboard_id)
        history = connection.execute(
            "SELECT count(*) FROM enterprise_dashboard_audit "
            "WHERE tenant_id=%s AND dashboard_id=%s",
            (tenant, dashboard_id),
        ).fetchone()
        assert int(history[0]) == 0


def test_postgres_dashboard_listing_has_deterministic_revision_and_id_order():
    psycopg = pytest.importorskip("psycopg")
    tenant = new_scope()
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        repository.initialize()
        second = repository.create(
            make_dashboard(tenant, "dashboard-b", title="Integration dashboard B"),
            idempotency_key="create-b",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        first = repository.create(
            make_dashboard(tenant, "dashboard-a", title="Integration dashboard A"),
            idempotency_key="create-a",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        assert [item.dashboard.dashboard_id for item in repository.list_for_tenant(tenant)] == [
            "dashboard-a", "dashboard-b"
        ]
        repository.update(
            replace(second.dashboard, title="Updated dashboard B"),
            expected_revision=1,
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(minutes=2),
        )
        assert [item.dashboard.dashboard_id for item in repository.list_for_tenant(tenant)] == [
            "dashboard-b", "dashboard-a"
        ]


def test_postgres_dashboard_exact_update_retry_is_idempotent_without_duplicate_audit():
    psycopg = pytest.importorskip("psycopg")
    tenant = new_scope()
    dashboard_id = f"dashboard-{uuid.uuid4().hex}"
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        repository.initialize()
        created = repository.create(
            make_dashboard(tenant, dashboard_id),
            idempotency_key="create-before-update-retry",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        connection.commit()

    requested_update = replace(created.dashboard, title="Updated once")
    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        first = repository.update(
            requested_update,
            expected_revision=1,
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(minutes=1),
        )
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        retry = repository.update(
            requested_update,
            expected_revision=1,
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(minutes=2),
        )
        assert retry == first
        assert len(repository.history(tenant, dashboard_id)) == 2


def test_postgres_dashboard_display_preferences_are_actor_and_tenant_scoped():
    psycopg = pytest.importorskip("psycopg")
    tenant = new_scope()
    other_tenant = new_scope()
    dashboard_id = f"dashboard-{uuid.uuid4().hex}"
    other_dashboard_id = f"dashboard-{uuid.uuid4().hex}"

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        repository.initialize()
        created = repository.create(
            make_dashboard(tenant, dashboard_id),
            idempotency_key="display-pref-owner",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        other_created = repository.create(
            make_dashboard(other_tenant, other_dashboard_id),
            idempotency_key="display-pref-other",
            actor_id="integration-owner",
            occurred_at=NOW + timedelta(seconds=1),
        )
        repository.replace_display_preferences(
            tenant,
            "integration-owner",
            ((dashboard_id, False, 0),),
            updated_at=NOW + timedelta(minutes=1),
        )
        repository.replace_display_preferences(
            other_tenant,
            "integration-owner",
            ((other_dashboard_id, True, 0),),
            updated_at=NOW + timedelta(minutes=1),
        )
        connection.commit()

    with psycopg.connect(DSN) as connection:
        repository = PostgresEnterpriseDashboardRepository(connection)
        assert repository.list_display_preferences(tenant, "integration-owner") == {
            dashboard_id: (False, 0)
        }
        assert repository.list_display_preferences(tenant, "another-user") == {}
        assert repository.list_display_preferences(other_tenant, "integration-owner") == {
            other_dashboard_id: (True, 0)
        }
        assert repository.get(tenant, dashboard_id).revision == created.revision
        assert repository.get(other_tenant, other_dashboard_id).revision == other_created.revision
