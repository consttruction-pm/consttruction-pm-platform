from datetime import datetime, timedelta, timezone
import json

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary, ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_cost_account_api import P6_COST_ACCOUNT_API_VERSION


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id, user_id, project_id, name):
        return ProjectSummary(project_id, tenant_id, name, 0)


class FakeCostAccountAPI:
    def __init__(self):
        self.accounts = {}
        self.calls = []

    def create(self, account, *, auth_context):
        account.validate()
        self.calls.append(("create", account, auth_context))
        key = (account.scope.tenant_id, account.scope.project_id, account.account_id)
        existing = self.accounts.get(key)
        if existing is not None and existing != account:
            raise ValueError("IMMUTABLE_COST_ACCOUNT")
        self.accounts[key] = account
        return self._dto(account)

    def get(self, scope, account_id, *, auth_context):
        self.calls.append(("get", scope, account_id, auth_context))
        account = self.accounts.get((scope.tenant_id, scope.project_id, account_id))
        if account is None:
            return None
        if account.scope.project_revision != scope.project_revision:
            raise ValueError("REVISION_CONFLICT")
        return self._dto(account)

    def list(self, scope, *, auth_context):
        self.calls.append(("list", scope, auth_context))
        return tuple(
            self._dto(account)
            for account in sorted(self.accounts.values(), key=lambda item: item.account_id)
            if account.scope.tenant_id == scope.tenant_id
            and account.scope.project_id == scope.project_id
            and account.scope.project_revision == scope.project_revision
        )

    @staticmethod
    def _dto(account):
        return {
            "contract_version": P6_COST_ACCOUNT_API_VERSION,
            "kind": "p6_cost_account",
            "scope": {
                "tenant_id": account.scope.tenant_id,
                "project_id": account.scope.project_id,
                "project_revision": account.scope.project_revision,
            },
            "cost_account": {
                "account_id": account.account_id,
                "name": account.name,
                "parent_account_id": account.parent_account_id,
                "description": account.description,
            },
        }


def routes():
    now = datetime(2026, 10, 9, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    fake = FakeCostAccountAPI()
    routes = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_cost_account_api=fake,
    )
    return routes, fake


def test_p6_cost_account_http_create_uses_authenticated_scope_and_preserves_version():
    routes, fake = routes()
    payload = {
        "account_id": "CA-01",
        "name": "Site establishment",
        "parent_account_id": None,
        "description": "Temporary facilities",
        "tenant_id": "spoofed-tenant",
        "project_id": "spoofed-project",
        "project_revision": 999,
    }
    status, _, body = routes.handle(
        "POST",
        "/api/projects/p1/p6/cost-accounts",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode(),
    )
    assert status == 200
    response = json.loads(body)
    assert response["contract_version"] == P6_COST_ACCOUNT_API_VERSION
    assert response["scope"] == {
        "tenant_id": "t1",
        "project_id": "p1",
        "project_revision": 2,
    }
    assert fake.calls[-1][1].scope == BackendScope("t1", "p1", 2)


def test_p6_cost_account_http_list_get_not_found_and_unknown_project():
    routes, fake = routes()
    payload = {"account_id": "CA-01", "name": "Site establishment"}
    status, _, _ = routes.handle(
        "POST", "/api/projects/p1/p6/cost-accounts",
        cookies={"cp_session": "s1"}, body=json.dumps(payload).encode(),
    )
    assert status == 200

    status, _, body = routes.handle(
        "GET", "/api/projects/p1/p6/cost-accounts", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body)["cost_accounts"][0]["cost_account"]["account_id"] == "CA-01"

    status, _, body = routes.handle(
        "GET", "/api/projects/p1/p6/cost-accounts/CA-01", cookies={"cp_session": "s1"}
    )
    assert status == 200
    assert json.loads(body)["cost_account"]["name"] == "Site establishment"

    status, _, body = routes.handle(
        "GET", "/api/projects/p1/p6/cost-accounts/missing", cookies={"cp_session": "s1"}
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_COST_ACCOUNT_NOT_FOUND"

    status, _, _ = routes.handle(
        "GET", "/api/projects/unknown/p6/cost-accounts", cookies={"cp_session": "s1"}
    )
    assert status == 403


def test_p6_cost_account_http_rejects_malformed_payload_and_missing_session():
    routes, _ = routes()
    status, _, _ = routes.handle(
        "POST", "/api/projects/p1/p6/cost-accounts",
        cookies={"cp_session": "s1"}, body=b"{",
    )
    assert status == 400

    status, _, _ = routes.handle(
        "GET", "/api/projects/p1/p6/cost-accounts"
    )
    assert status == 401
