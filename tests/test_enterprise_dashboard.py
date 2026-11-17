from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import Permission
from construction_pm.application.project_lifecycle import ProjectLifecycleError, SessionError
from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.control_intelligence.portfolio import (
    PortfolioControlSnapshot,
    PortfolioProjectControlInput,
)
from construction_pm.control_intelligence.portfolio_decision import PortfolioDecisionBoundary
from construction_pm.enterprise_dashboard import (
    DashboardFilter,
    DashboardLayout,
    DashboardPortlet,
    EnterpriseDashboard,
    EnterpriseDashboardError,
    PORTFOLIO_CONTROL_SNAPSHOT,
    PORTFOLIO_DECISION,
)
from construction_pm.enterprise_dashboard_application import (
    EnterpriseDashboardApplicationService,
    EnterpriseDashboardAuthorizationError,
    EnterpriseDashboardSourceError,
)
from construction_pm.enterprise_dashboard_repository import (
    StoredEnterpriseDashboard,
)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def snapshot(
    tenant_id: str = "tenant-a",
    portfolio_id: str = "portfolio-1",
    *,
    generated_at: datetime = NOW,
) -> PortfolioControlSnapshot:
    return PortfolioControlSnapshot(
        snapshot_id="snapshot-1",
        portfolio_id=portfolio_id,
        tenant_id=tenant_id,
        generated_at=generated_at,
        projects=(
            PortfolioProjectControlInput(
                "project-1", 7, "included", "active", name_key="project.one"
            ),
        ),
        source_refs=(SourceReference("source-1", "portfolio", "/portfolio/project-1", 7),),
    )


def snapshot_portlet(
    *,
    instance_id: str = "portlet-1",
    portfolio_id: str = "portfolio-1",
    layout: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "instance_id": instance_id,
        "type_id": PORTFOLIO_CONTROL_SNAPSHOT,
        "contract_version": PORTFOLIO_CONTROL_SNAPSHOT,
        "config": {"portfolio_id": portfolio_id},
        "layout": layout or {"x": 0, "y": 0, "w": 6, "h": 4},
    }


def decision_portlet() -> dict[str, object]:
    return {
        "instance_id": "decision-1",
        "type_id": PORTFOLIO_DECISION,
        "contract_version": PORTFOLIO_DECISION,
        "config": {"portfolio_id": "portfolio-1", "decision_id": "decision-1"},
        "layout": {"x": 6, "y": 0, "w": 6, "h": 4},
    }


def create_payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Executive overview",
        "description": "Portfolio snapshot",
        "context": "enterprise_home",
        "context_portfolio_id": None,
        "portlets": [snapshot_portlet()],
        "filters": [
            {"key": "membership_status", "operator": "eq", "value": "included"}
        ],
    }
    payload.update(overrides)
    return payload


class FakeRepository:
    def __init__(self):
        self.items: dict[tuple[str, str], StoredEnterpriseDashboard] = {}
        self.idempotency: dict[tuple[str, str, str], tuple[str, StoredEnterpriseDashboard]] = {}

    @staticmethod
    def _fingerprint(dashboard):
        data = dashboard.as_dict()
        for key in ("dashboard_id", "revision", "created_at", "updated_at"):
            data.pop(key, None)
        return repr(data)

    def create(self, dashboard, *, idempotency_key, actor_id, occurred_at, event_type="created"):
        key = (dashboard.tenant_id, dashboard.owner_user_id, idempotency_key)
        fingerprint = self._fingerprint(dashboard)
        if key in self.idempotency:
            existing_fingerprint, stored = self.idempotency[key]
            if fingerprint != existing_fingerprint:
                raise ValueError("ENTERPRISE_DASHBOARD_IDEMPOTENCY_KEY_REUSE")
            return stored
        stored = StoredEnterpriseDashboard(dashboard, 1)
        self.items[(dashboard.tenant_id, dashboard.dashboard_id)] = stored
        self.idempotency[key] = (fingerprint, stored)
        return stored

    def get(self, tenant_id, dashboard_id):
        try:
            return self.items[(tenant_id, dashboard_id)]
        except KeyError:
            raise KeyError("ENTERPRISE_DASHBOARD_NOT_FOUND") from None

    def list_for_tenant(self, tenant_id, *, limit=200):
        return tuple(
            item for (tenant, _), item in self.items.items() if tenant == tenant_id
        )[:limit]

    def update(self, dashboard, *, expected_revision, actor_id, occurred_at, event_type="updated"):
        current = self.get(dashboard.tenant_id, dashboard.dashboard_id)
        if current.revision != expected_revision:
            from construction_pm.enterprise_dashboard import EnterpriseDashboardRevisionConflict
            raise EnterpriseDashboardRevisionConflict("ENTERPRISE_DASHBOARD_REVISION_CONFLICT")
        updated = replace(
            dashboard,
            revision=expected_revision + 1,
            updated_at=occurred_at,
        )
        stored = StoredEnterpriseDashboard(updated, expected_revision + 1)
        self.items[(dashboard.tenant_id, dashboard.dashboard_id)] = stored
        return stored


class FakeLifecycle:
    def __init__(self):
        self.sessions = {
            "alice-session": SimpleNamespace(
                user_id="alice", tenant_id="tenant-a",
                roles=frozenset({"enterprise_user"}),
            ),
            "bob-session": SimpleNamespace(
                user_id="bob", tenant_id="tenant-a",
                roles=frozenset({"enterprise_viewer"}),
            ),
            "admin-session": SimpleNamespace(
                user_id="admin", tenant_id="tenant-a",
                roles=frozenset({"enterprise_admin"}),
            ),
            "other-tenant-session": SimpleNamespace(
                user_id="other", tenant_id="tenant-b",
                roles=frozenset({"enterprise_user"}),
            ),
        }
        self.project_grants = {
            ("alice-session", "project-1"),
            ("admin-session", "project-1"),
        }

    def get_session(self, session_id, *, now):
        if session_id not in self.sessions:
            raise SessionError("SESSION_INVALID")
        return self.sessions[session_id]

    def authorize_project(self, session_id, project_id, permission, *, now):
        if (session_id, project_id) not in self.project_grants or permission != Permission.PROJECT_READ:
            raise ProjectLifecycleError("PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED")
        session = self.sessions[session_id]
        return SimpleNamespace(
            context=SimpleNamespace(tenant_id=session.tenant_id, project_id=project_id)
        )


class FakePortfolioQuery:
    def __init__(self, result=None):
        self.result = result or snapshot()
        self.calls = []

    def get_snapshot(self, portfolio_id, *, auth_context):
        self.calls.append((portfolio_id, auth_context.tenant_id, auth_context.user_id))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakePortfolioDecisionAPI:
    def __init__(self):
        decision = PortfolioDecisionBoundary(
            decision_id="decision-1",
            portfolio_id="portfolio-1",
            tenant_id="tenant-a",
            status="proposed",
            decision_type="review",
            title_key="decision.review",
            affected_project_ids=("project-1",),
            source_snapshot_id="snapshot-1",
            evidence_refs=(
                SourceReference("decision-source-1", "portfolio", "/decisions/decision-1", 3),
            ),
        )
        self.result = {**decision.as_dict(), "revision": 4}

    def get(self, request, *, auth_context):
        assert request.tenant_id == auth_context.tenant_id
        return self.result


def make_service(*, source=None, decision_api=None):
    lifecycle = FakeLifecycle()
    repository = FakeRepository()
    query = source or FakePortfolioQuery()
    service = EnterpriseDashboardApplicationService(
        repository,
        lifecycle,
        portfolio_query_service=query,
        portfolio_decision_api=decision_api or FakePortfolioDecisionAPI(),
        clock=lambda: NOW,
    )
    return service, repository, lifecycle, query


def create_dashboard(service, *, session_id="alice-session", payload=None):
    return service.create_dashboard(
        session_id,
        payload or create_payload(),
        idempotency_key="create-dashboard-1",
    )


def test_create_derives_tenant_and_owner_from_authenticated_session():
    service, _, _, _ = make_service()
    stored = create_dashboard(service)
    assert stored.dashboard.tenant_id == "tenant-a"
    assert stored.dashboard.owner_user_id == "alice"
    assert stored.dashboard.revision == 1
    assert stored.dashboard.visibility == "private"


def test_create_rejects_caller_supplied_authority_fields():
    service, _, _, _ = make_service()
    payload = create_payload(tenant_id="tenant-forged", owner_user_id="attacker")
    with pytest.raises(EnterpriseDashboardError, match="CREATE_FIELDS"):
        create_dashboard(service, payload=payload)


def test_contract_rejects_unknown_portlet_type_bad_layout_and_unregistered_filters():
    with pytest.raises(EnterpriseDashboardError, match="UNKNOWN_ENTERPRISE_DASHBOARD_PORTLET_TYPE"):
        DashboardPortlet.from_dict(
            {
                "instance_id": "bad",
                "type_id": "arbitrary-sql.v1",
                "contract_version": "arbitrary-sql.v1",
                "config": {},
                "layout": {"x": 0, "y": 0, "w": 1, "h": 1},
            },
            context="enterprise_home",
            context_portfolio_id=None,
        )
    with pytest.raises(EnterpriseDashboardError, match="OUT_OF_BOUNDS"):
        DashboardLayout(10, 0, 3, 1).validate()
    with pytest.raises(EnterpriseDashboardError, match="UNKNOWN_ENTERPRISE_DASHBOARD_FILTER"):
        DashboardFilter("external_url", "eq", "https://example.com").validate()


def test_portlet_configuration_is_closed_and_context_bound():
    invalid = snapshot_portlet()
    invalid["config"] = {"portfolio_id": "portfolio-1", "sql": "select 1"}
    with pytest.raises(EnterpriseDashboardError, match="PORTLET_CONFIG"):
        DashboardPortlet.from_dict(
            invalid, context="enterprise_home", context_portfolio_id=None
        )
    with pytest.raises(EnterpriseDashboardError, match="CONTEXT_MISMATCH"):
        DashboardPortlet.from_dict(
            snapshot_portlet(portfolio_id="portfolio-2"),
            context="portfolio",
            context_portfolio_id="portfolio-1",
        )


def test_explicit_user_share_grants_definition_read_then_revocation_removes_it():
    service, _, _, _ = make_service()
    created = create_dashboard(service)
    with pytest.raises(Exception):
        service.get_dashboard("bob-session", created.dashboard.dashboard_id)
    shared = service.assign_share(
        "alice-session",
        created.dashboard.dashboard_id,
        target_type="user",
        target_id="bob",
        expected_revision=1,
    )
    assert shared.dashboard.visibility == "users"
    assert service.get_dashboard("bob-session", created.dashboard.dashboard_id).dashboard.title == "Executive overview"
    revoked = service.revoke_share(
        "alice-session",
        created.dashboard.dashboard_id,
        target_type="user",
        target_id="bob",
        expected_revision=2,
    )
    assert revoked.dashboard.visibility == "private"
    with pytest.raises(Exception):
        service.get_dashboard("bob-session", created.dashboard.dashboard_id)


def test_explicit_role_share_and_admin_management():
    service, _, _, _ = make_service()
    created = create_dashboard(service)
    shared = service.assign_share(
        "alice-session",
        created.dashboard.dashboard_id,
        target_type="role",
        target_id="enterprise_viewer",
        expected_revision=1,
    )
    assert shared.dashboard.shared_role_ids == ("enterprise_viewer",)
    assert service.get_dashboard("bob-session", created.dashboard.dashboard_id).revision == 2
    updated = service.update_dashboard(
        "admin-session",
        created.dashboard.dashboard_id,
        {"title": "Admin revised title"},
        expected_revision=2,
    )
    assert updated.dashboard.title == "Admin revised title"


def test_shared_viewer_cannot_change_dashboard_and_revision_conflicts_fail():
    service, _, _, _ = make_service()
    created = create_dashboard(service)
    service.assign_share(
        "alice-session",
        created.dashboard.dashboard_id,
        target_type="user",
        target_id="bob",
        expected_revision=1,
    )
    with pytest.raises(EnterpriseDashboardAuthorizationError):
        service.update_dashboard(
            "bob-session",
            created.dashboard.dashboard_id,
            {"title": "Not allowed"},
            expected_revision=2,
        )
    with pytest.raises(Exception, match="REVISION_CONFLICT"):
        service.update_dashboard(
            "alice-session",
            created.dashboard.dashboard_id,
            {"title": "Stale write"},
            expected_revision=1,
        )


def test_duplicate_creates_private_copy_owned_by_current_actor_and_is_idempotent():
    service, _, _, _ = make_service()
    created = create_dashboard(service)
    service.assign_share(
        "alice-session",
        created.dashboard.dashboard_id,
        target_type="user",
        target_id="bob",
        expected_revision=1,
    )
    service._lifecycle.sessions["bob-session"].roles = frozenset({"enterprise_user"})
    first = service.duplicate_dashboard(
        "bob-session", created.dashboard.dashboard_id, idempotency_key="copy-1"
    )
    second = service.duplicate_dashboard(
        "bob-session", created.dashboard.dashboard_id, idempotency_key="copy-1"
    )
    assert first == second
    assert first.dashboard.owner_user_id == "bob"
    assert first.dashboard.visibility == "private"
    assert first.dashboard.dashboard_id != created.dashboard.dashboard_id


def test_cross_tenant_guessed_dashboard_id_does_not_disclose_record():
    service, _, _, _ = make_service()
    created = create_dashboard(service)
    with pytest.raises(Exception):
        service.get_dashboard("other-tenant-session", created.dashboard.dashboard_id)


def test_archived_dashboard_is_hidden_from_shared_users_but_remains_with_owner():
    service, _, _, _ = make_service()
    created = create_dashboard(service)
    service.assign_share(
        "alice-session",
        created.dashboard.dashboard_id,
        target_type="user",
        target_id="bob",
        expected_revision=1,
    )
    archived = service.archive_dashboard(
        "alice-session", created.dashboard.dashboard_id, expected_revision=2
    )
    assert archived.dashboard.status == "archived"
    assert service.get_dashboard("alice-session", created.dashboard.dashboard_id).dashboard.status == "archived"
    with pytest.raises(Exception):
        service.get_dashboard("bob-session", created.dashboard.dashboard_id)


def test_dashboard_share_never_bypasses_source_project_authorization():
    service, _, lifecycle, _ = make_service()
    created = create_dashboard(service)
    service.assign_share(
        "alice-session",
        created.dashboard.dashboard_id,
        target_type="user",
        target_id="bob",
        expected_revision=1,
    )
    with pytest.raises(EnterpriseDashboardAuthorizationError, match="SOURCE_PROJECT_NOT_AUTHORIZED"):
        service.read_portlets("bob-session", created.dashboard.dashboard_id)
    lifecycle.project_grants.add(("bob-session", "project-1"))
    result = service.read_portlets("bob-session", created.dashboard.dashboard_id)
    assert result["portlets"][0]["freshness_state"] == "fresh"
    assert result["portlets"][0]["source_snapshot_id"] == "snapshot-1"
    assert result["portlets"][0]["source_revision"] == "source-1:7"


def test_stale_and_missing_source_states_are_explicit():
    stale_query = FakePortfolioQuery(
        snapshot(generated_at=NOW - timedelta(days=3))
    )
    service, _, _, _ = make_service(source=stale_query)
    created = create_dashboard(service)
    stale = service.read_portlets("alice-session", created.dashboard.dashboard_id)
    assert stale["portlets"][0]["freshness_state"] == "stale"

    missing_service, _, _, _ = make_service(source=FakePortfolioQuery(KeyError("missing")))
    missing_dashboard = create_dashboard(missing_service)
    missing = missing_service.read_portlets(
        "alice-session", missing_dashboard.dashboard.dashboard_id
    )
    assert missing["portlets"][0]["freshness_state"] == "missing"
    assert missing["portlets"][0]["data"] is None


def test_portfolio_decision_portlet_reauthorizes_affected_projects_and_preserves_revision():
    service, repository, lifecycle, _ = make_service()
    created = service.create_dashboard(
        "alice-session",
        create_payload(portlets=[decision_portlet()]),
        idempotency_key="decision-dashboard",
    )
    result = service.read_portlets("alice-session", created.dashboard.dashboard_id)
    assert result["portlets"][0]["source_revision"] == 4
    assert result["portlets"][0]["freshness_state"] == "unknown"
    lifecycle.project_grants.remove(("alice-session", "project-1"))
    with pytest.raises(EnterpriseDashboardAuthorizationError):
        service.read_portlets("alice-session", created.dashboard.dashboard_id)


def test_portfolio_context_creation_requires_authorized_source_scope():
    service, _, lifecycle, _ = make_service()
    lifecycle.project_grants.remove(("alice-session", "project-1"))
    with pytest.raises(EnterpriseDashboardAuthorizationError):
        create_dashboard(
            service,
            payload=create_payload(
                context="portfolio",
                context_portfolio_id="portfolio-1",
            ),
        )


def test_enterprise_viewer_cannot_create_or_share_and_non_enterprise_user_is_denied():
    service, _, _, _ = make_service()
    with pytest.raises(EnterpriseDashboardAuthorizationError, match="WRITE_DENIED"):
        create_dashboard(service, session_id="bob-session")
    service._lifecycle.sessions["project-only-session"] = SimpleNamespace(
        user_id="project-only",
        tenant_id="tenant-a",
        roles=frozenset({"project_manager"}),
    )
    with pytest.raises(EnterpriseDashboardAuthorizationError, match="ACCESS_DENIED"):
        service.list_dashboards("project-only-session")


def test_portlet_read_requires_configured_source_adapter():
    lifecycle = FakeLifecycle()
    service = EnterpriseDashboardApplicationService(
        FakeRepository(), lifecycle, portfolio_query_service=None, clock=lambda: NOW
    )
    created = create_dashboard(service)
    with pytest.raises(EnterpriseDashboardSourceError, match="NOT_CONFIGURED"):
        service.read_portlets("alice-session", created.dashboard.dashboard_id)


def test_dashboard_definition_round_trips_and_rejects_unknown_fields():
    service, _, _, _ = make_service()
    stored = create_dashboard(service)
    payload = stored.dashboard.as_dict()
    restored = EnterpriseDashboard.from_dict(payload)
    assert restored == stored.dashboard
    payload["unexpected"] = "must reject"
    with pytest.raises(EnterpriseDashboardError, match="FIELDS"):
        EnterpriseDashboard.from_dict(payload)


def test_dashboard_schema_is_closed_and_declares_read_freshness_contract():
    root = Path(__file__).parents[1]
    schema = json.loads(
        (root / "shared" / "contracts" / "enterprise-dashboard.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["contract_version"]["const"] == "cubi-enterprise-dashboard.v1"
    assert schema["properties"]["portlets"]["maxItems"] == 12
    assert schema["$defs"]["portlet_read_response"]["additionalProperties"] is False
    assert schema["$defs"]["portlet_read_response"]["properties"]["freshness_state"]["enum"] == [
        "fresh", "stale", "missing", "unknown"
    ]
    assert schema["$defs"]["dashboard_read_response"]["properties"]["contract_version"]["const"] == (
        "cubi-enterprise-dashboard-read.v1"
    )


ORACLE_HELP_TRACEABILITY_URLS = (
    "https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/7826.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/7827.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/7831.htm",
    "https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/5989.html",
    "https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/portfolioanalysissettingsarea-9110a.html",
    "https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/5959.html",
    "https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7858.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/7856.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/43796.htm",
    "https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-reports/portfolioreports-63041a.html",
    "https://primavera.oraclecloud.com/help/en/user/90205.htm",
    "https://primavera.oraclecloud.com/help/en/user/81716.htm",
    "https://primavera.oraclecloud.com/help/en/user/81707_1.htm",
    "https://primavera.oraclecloud.com/help/en/user/100616.htm",
    "https://primavera.oraclecloud.com/help/en/user/99393.htm",
    "https://primavera.oraclecloud.com/help/en/user/99399.htm",
    "https://primavera.oraclecloud.com/help/en/user/144444.htm",
    "https://primavera.oraclecloud.com/help/en/user/91076.htm",
    "https://primavera.oraclecloud.com/help/en/user/91079.htm",
    "https://primavera.oraclecloud.com/help/en/user/102753_2.htm",
    "https://primavera.oraclecloud.com/help/en/user/99151.htm",
    "https://primavera.oraclecloud.com/help/en/user/102917.htm",
    "https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",
    "https://docs.oracle.com/cd/G48902_01/client_help/en_US/usingportfolios.htm",
    "https://docs.oracle.com/cd/G48902_01/client_help/en_US/portfolios.htm",
    "https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_portfolio.htm",
    "https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm",
    "https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-tm/p6-tmw_overview-51690a.html",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/32010.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/32012.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/32008.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/47039.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/6667.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/44303.htm",
    "https://docs.oracle.com/cd/G48897_01/p6help/en/44295.htm",
    "https://primavera.oraclecloud.com/help/en/user/142302.htm",
    "https://primavera.oraclecloud.com/help/en/user/178503.htm",
    "https://primavera.oraclecloud.com/help/en/user/142305.htm",
    "https://primavera.oraclecloud.com/help/en/user/95937.htm",
    "https://primavera.oraclecloud.com/help/en/user/96011.htm",
)


def test_official_oracle_help_sources_have_exact_documentation_traceability():
    root = Path(__file__).parents[1]
    document = (
        root / "docs" / "enterprise" / "ENT06_DASHBOARDS_PORTLETS_IMPLEMENTATION_V1.md"
    ).read_text(encoding="utf-8")
    assert len(ORACLE_HELP_TRACEABILITY_URLS) == 42
    for url in ORACLE_HELP_TRACEABILITY_URLS:
        assert url in document
    for disposition in ("Partial", "Not Applicable", "Deferred"):
        assert disposition in document
    for navigation_or_access_term in (
        "Navigation Menu",
        "Access tab",
        "OBS access",
        "Available Tiles",
        "Manual/Automatic",
    ):
        assert navigation_or_access_term in document
