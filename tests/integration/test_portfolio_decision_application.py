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


def decision(**overrides):
    values = dict(
        decision_id="D-1",
        portfolio_id="P-1",
        tenant_id="T-1",
        status="proposed",
        decision_type="review",
        title_key="decision.review",
        evidence_refs=(SourceReference("S-1", "snapshot", "$.portfolio", 1),),
    )
    values.update(overrides)
    return PortfolioDecisionBoundary(**values)
