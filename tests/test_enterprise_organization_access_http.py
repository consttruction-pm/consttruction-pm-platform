from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from types import SimpleNamespace

from construction_pm.enterprise_organization_access import (
    EnterpriseTeam,
    EnterpriseTeamMembership,
)
from construction_pm.enterprise_organization_access_http import EnterpriseOrganizationAccessHttpMiddleware

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


class Service:
    def __init__(self):
        self.team = EnterpriseTeam("tenant", "team-1", "Controls", "owner", "active", 1, NOW)
        self.membership = EnterpriseTeamMembership(
            "tenant", "team-1", "owner", "owner", "active", (), 1, NOW
        )
        self.calls = []

    def list_my_teams(self, session_id):
        self.calls.append(("list", session_id))
        return (self.team,)

    def create_team(self, session_id, name):
        self.calls.append(("create", session_id, name))
        return self.team

    def add_member(self, session_id, team_id, user_id, role, *, scope_project_ids=()):
        self.calls.append(("add", session_id, team_id, user_id, role, scope_project_ids))
        return EnterpriseTeamMembership(
            "tenant", team_id, user_id, role, "active", tuple(scope_project_ids), 1, NOW
        )

    def remove_member(self, session_id, team_id, user_id, *, expected_revision):
        self.calls.append(("remove", session_id, team_id, user_id, expected_revision))
        return EnterpriseTeamMembership(
            "tenant", team_id, user_id, "member", "removed", (), expected_revision + 1, NOW, NOW
        )


def request(app, method, path, payload=None, *, cookie="cp_session=session-1"):
    raw = b"" if payload is None else json.dumps(payload).encode()
    environ = {
        "REQUEST_METHOD": method, "PATH_INFO": path, "HTTP_COOKIE": cookie,
        "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw),
    }
    captured = {}
    def start(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)
    body = b"".join(app(environ, start))
    return captured["status"], json.loads(body)


def payload(**values):
    return {"contract_version": "cubi-enterprise-team.v1", **values}


def test_authenticated_team_list_and_create_use_versioned_contract():
    service = Service()
    app = EnterpriseOrganizationAccessHttpMiddleware(lambda *_: [b"fallback"], service)
    status, body = request(app, "GET", "/api/enterprise/teams")
    assert status == "200 OK"
    assert body["teams"][0]["team_id"] == "team-1"

    status, body = request(app, "POST", "/api/enterprise/teams", payload(name="Controls"))
    assert status == "201 Created"
    assert body["team"]["name"] == "Controls"
    assert service.calls[-1] == ("create", "session-1", "Controls")


def test_membership_add_and_revision_guarded_removal_are_routed():
    service = Service()
    app = EnterpriseOrganizationAccessHttpMiddleware(lambda *_: [b"fallback"], service)
    status, body = request(
        app, "POST", "/api/enterprise/teams/team-1/members",
        payload(user_id="worker-1", role="field_worker", scope_project_ids=["p-1"]),
    )
    assert status == "201 Created"
    assert body["membership"]["scope_project_ids"] == ["p-1"]

    status, body = request(
        app, "DELETE", "/api/enterprise/teams/team-1/members/worker-1",
        payload(expected_revision=1),
    )
    assert status == "200 OK"
    assert body["membership"]["status"] == "removed"
    assert service.calls[-1] == ("remove", "session-1", "team-1", "worker-1", 1)


def test_team_routes_fail_closed_without_session_or_contract():
    service = Service()
    app = EnterpriseOrganizationAccessHttpMiddleware(lambda *_: [b"fallback"], service)
    status, body = request(app, "GET", "/api/enterprise/teams", cookie="")
    assert status == "401 Unauthorized"
    assert body["code"] == "SESSION_REQUIRED"

    status, body = request(app, "POST", "/api/enterprise/teams", {"name": "No version"})
    assert status == "400 Bad Request"
    assert body["code"] == "UNSUPPORTED_ENTERPRISE_TEAM_CONTRACT"


def test_unowned_routes_are_delegated():
    app = EnterpriseOrganizationAccessHttpMiddleware(
        lambda *_: [b"delegated"], Service()
    )
    assert app({"PATH_INFO": "/api/enterprise/tasks"}, lambda *_: None) == [b"delegated"]
