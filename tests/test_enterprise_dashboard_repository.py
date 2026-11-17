from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from construction_pm.enterprise_dashboard import (
    DashboardFilter,
    DashboardLayout,
    DashboardPortlet,
    EnterpriseDashboard,
    EnterpriseDashboardError,
    PORTFOLIO_CONTROL_SNAPSHOT,
)
from construction_pm.enterprise_dashboard_repository import (
    PostgresEnterpriseDashboardRepository,
)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def dashboard(
    dashboard_id: str = "dashboard-1",
    *,
    created_at: datetime = NOW,
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
        tenant_id="tenant-a",
        context="enterprise_home",
        context_portfolio_id=None,
        owner_user_id="alice",
        title="Executive overview",
        description="",
        status="active",
        visibility="private",
        shared_user_ids=(),
        shared_role_ids=(),
        portlets=(portlet,),
        filters=(DashboardFilter("membership_status", "eq", "included"),),
        revision=1,
        created_at=created_at,
    )


class RecordingConnection:
    def __init__(self):
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        return self


class IdentityLookupConnection:
    def __init__(self, row):
        self.row = row
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        return self

    def fetchone(self):
        return self.row


def test_user_share_target_lookup_requires_active_same_tenant_identity():
    same_tenant = PostgresEnterpriseDashboardRepository(
        IdentityLookupConnection(("tenant-a", True))
    )
    assert same_tenant.user_belongs_to_tenant("tenant-a", "bob") is True

    cross_tenant = PostgresEnterpriseDashboardRepository(
        IdentityLookupConnection(("tenant-b", True))
    )
    assert cross_tenant.user_belongs_to_tenant("tenant-a", "bob") is False

    inactive = PostgresEnterpriseDashboardRepository(
        IdentityLookupConnection(("tenant-a", False))
    )
    assert inactive.user_belongs_to_tenant("tenant-a", "bob") is False


def test_dashboard_repository_serialization_round_trip_is_lossless():
    original = dashboard()
    encoded = PostgresEnterpriseDashboardRepository._serialize(original)
    restored = PostgresEnterpriseDashboardRepository._deserialize(encoded)
    assert restored == original


def test_create_fingerprint_ignores_generated_identity_and_timestamps():
    first = dashboard("dashboard-first")
    second = dashboard(
        "dashboard-retry",
        created_at=datetime(2026, 11, 17, 12, 5, tzinfo=timezone.utc),
    )
    assert (
        PostgresEnterpriseDashboardRepository._fingerprint(first)
        == PostgresEnterpriseDashboardRepository._fingerprint(second)
    )


def test_create_fingerprint_changes_when_dashboard_configuration_changes():
    first = dashboard()
    changed = replace(first, title="Different title")
    assert (
        PostgresEnterpriseDashboardRepository._fingerprint(first)
        != PostgresEnterpriseDashboardRepository._fingerprint(changed)
    )


def test_initialize_creates_tenant_scoped_tables_and_append_only_audit_trigger():
    connection = RecordingConnection()
    repository = PostgresEnterpriseDashboardRepository(connection)
    repository.initialize()
    sql = "\n".join(statement for statement, _ in connection.statements)
    assert "CREATE TABLE IF NOT EXISTS enterprise_dashboards" in sql
    assert "PRIMARY KEY (tenant_id, dashboard_id)" in sql
    assert "CREATE TABLE IF NOT EXISTS enterprise_dashboard_idempotency" in sql
    assert "CREATE TABLE IF NOT EXISTS enterprise_dashboard_audit" in sql
    assert "CREATE TABLE IF NOT EXISTS enterprise_dashboard_display_preferences" in sql
    assert "PRIMARY KEY (tenant_id, user_id, dashboard_id)" in sql
    assert "ON DELETE RESTRICT" in sql
    assert "ENTERPRISE_DASHBOARD_AUDIT_APPEND_ONLY" in sql
    assert "BEFORE UPDATE OR DELETE ON enterprise_dashboard_audit" in sql


def test_repository_rejects_invalid_audit_timestamp_and_event_type():
    with pytest.raises(EnterpriseDashboardError, match="TIMEZONE_AWARE"):
        PostgresEnterpriseDashboardRepository._validate_metadata(
            "key",
            "alice",
            datetime(2026, 11, 17, 12, 0),
            "created",
        )
    with pytest.raises(EnterpriseDashboardError, match="AUDIT_EVENT"):
        PostgresEnterpriseDashboardRepository._validate_metadata(
            "key",
            "alice",
            NOW,
            "deleted",
        )


def test_dashboard_identity_is_immutable_across_revisions():
    original = dashboard()
    changed = replace(original, owner_user_id="bob")
    assert (
        PostgresEnterpriseDashboardRepository._identity(original)
        != PostgresEnterpriseDashboardRepository._identity(changed)
    )
