from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, Permission, RoleBasedAuthorizationPolicy
from construction_pm.control_intelligence import PortfolioDecisionBoundary, SourceReference
from construction_pm.portfolio_decision_application import PortfolioDecisionApplicationService
from construction_pm.portfolio_decision_persistence import PostgresPortfolioDecisionStore


class Cursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class Connection:
    def __init__(self):
        self.rows = {}
        self.audit = []

    def execute(self, sql, params=()):
        if sql.startswith("SELECT decision_json, decision_revision"):
            return Cursor(self.rows.get(("decision", *params)))
        if sql.startswith("SELECT decision_id, fingerprint"):
            return Cursor(self.rows.get(("idem", *params)))
        if sql.startswith("SELECT decision_revision, event_type"):
            return Cursor(rows=self.audit)
        if sql.startswith("INSERT INTO portfolio_decisions"):
            self.rows[("decision", params[0], params[1], params[2])] = (params[6], params[5])
            self.rows[("idem", params[0], params[1], params[3])] = (params[2], params[4], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO portfolio_decision_audit"):
            self.audit.append((params[3], params[4], params[5], params[6]))
            return Cursor()
        if sql.startswith("UPDATE portfolio_decisions"):
            key = ("decision", params[2], params[3], params[4])
            self.rows[key] = (params[1], params[0])
            return Cursor()
        if "FOR UPDATE" in sql:
            return Cursor(self.rows.get(("decision", *params)))
        return Cursor()


def policy():
    return RoleBasedAuthorizationPolicy({
        "project_admin": frozenset({Permission.PROJECT_ADMIN, Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        "viewer": frozenset({Permission.PROJECT_READ}),
    })


def decision():
    return PortfolioDecisionBoundary(
        decision_id="D-1",
        portfolio_id="P-1",
        tenant_id="T-1",
        status="proposed",
        decision_type="review",
        title_key="decision.review",
        evidence_refs=(SourceReference("S-1", "snapshot", "$.portfolio", 1),),
    )


def context(user_id="admin-1", role="project_admin", tenant_id="T-1"):
    return AuthorizationContext(tenant_id=tenant_id, project_id="portfolio-scope", user_id=user_id, roles=frozenset({role}))


def test_create_enforces_tenant_scope_and_actor_identity():
    store = PostgresPortfolioDecisionStore(Connection())
    service = PortfolioDecisionApplicationService(store, policy())
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    created = service.create(
        decision(),
        context=context(),
        idempotency_key="k-1",
        actor_id="admin-1",
        occurred_at=now,
    )

    assert created.decision_revision == 1
    assert created.decision.decision_id == "D-1"

    with pytest.raises(AuthorizationError, match="ACTOR_MISMATCH"):
        service.create(
            decision(decision_id="D-2"),
            context=context(),
            idempotency_key="k-2",
            actor_id="other-user",
            occurred_at=now,
        )


def test_create_rejects_cross_tenant_decision():
    service = PortfolioDecisionApplicationService(PostgresPortfolioDecisionStore(Connection()), policy())
    with pytest.raises(AuthorizationError, match="CROSS_TENANT"):
        service.create(
            PortfolioDecisionBoundary(
                decision_id="D-2",
                portfolio_id="P-1",
                tenant_id="T-2",
                status="proposed",
                decision_type="review",
                title_key="decision.review",
                evidence_refs=(SourceReference("S-1", "snapshot", "$.portfolio", 1),),
            ),
            context=context(),
            idempotency_key="k-2",
            actor_id="admin-1",
            occurred_at=datetime.now(timezone.utc),
        )


def test_approve_sets_authoritative_actor_and_persists_transition():
    service = PortfolioDecisionApplicationService(PostgresPortfolioDecisionStore(Connection()), policy())
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
    created = service.create(
        decision(),
        context=context(),
        idempotency_key="k-1",
        actor_id="admin-1",
        occurred_at=now,
    )

    approved = service.approve(
        decision(),
        context=context(),
        expected_decision_revision=created.decision_revision,
        approved_at=datetime(2026, 9, 27, 15, 5, tzinfo=timezone.utc),
    )

    assert approved.decision_revision == 2
    assert approved.decision.status == "approved"
    assert approved.decision.approved_by == "admin-1"
