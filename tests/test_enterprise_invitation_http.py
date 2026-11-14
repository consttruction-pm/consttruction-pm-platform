from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from construction_pm.enterprise_invitation_http import EnterpriseInvitationHttpMiddleware


class Service:
    def list_received(self, session_id):
        return (type("Invitation", (), {
            "invitation_id":"invite-inbox-1","team_id":"team-1","role":"member",
            "status":"pending","expires_at":datetime(2026,11,22,tzinfo=timezone.utc),
            "created_at":datetime(2026,11,15,tzinfo=timezone.utc),"token":None,
        })(),)

    def lookup(self, session_id, value):
        return type("Identity", (), {"cubi_id":"CUBI-2345-6789-ABCD","display_name":"Member"})()

    def invite(self, session_id, team_id, cubi_id, role):
        return type("Invitation", (), {
            "invitation_id":"invite-1","team_id":team_id,"role":role,"status":"pending",
            "expires_at":datetime(2026,11,22,tzinfo=timezone.utc),
            "created_at":datetime(2026,11,15,tzinfo=timezone.utc),"token":"one-time-secret",
        })()


def _request(app, path, *, method="GET", body=None, cookie="cp_session=session-1", query=""):
    raw = json.dumps(body or {}).encode()
    environ = {
        "REQUEST_METHOD":method,"PATH_INFO":path,"QUERY_STRING":query,
        "HTTP_COOKIE":cookie,"CONTENT_LENGTH":str(len(raw)),"wsgi.input":io.BytesIO(raw),
    }
    result = {}
    def start(status, headers):
        result["status"] = status
        result["headers"] = headers
    result["body"] = b"".join(app(environ, start))
    return result


def test_invitation_http_requires_session_and_never_exposes_private_identity_fields():
    app = EnterpriseInvitationHttpMiddleware(lambda e,s: [b"fallback"], Service())
    missing = _request(app, "/api/enterprise/cubi-id", cookie="")
    assert missing["status"].startswith("401")
    response = _request(app, "/api/enterprise/cubi-id", query="value=CUBI-2345-6789-ABCD")
    payload = json.loads(response["body"])
    assert response["status"].startswith("200")
    assert payload["identity"] == {"cubi_id":"CUBI-2345-6789-ABCD","display_name":"Member"}
    assert "email" not in payload["identity"]


def test_invitation_http_returns_one_time_token_only_on_creation():
    app = EnterpriseInvitationHttpMiddleware(lambda e,s: [b"fallback"], Service())
    response = _request(
        app, "/api/enterprise/teams/team-1/invitations", method="POST",
        body={"contract_version":"cubi-team-invitation.v1","cubi_id":"CUBI-2345-6789-ABCD","role":"member"},
    )
    payload = json.loads(response["body"])
    assert response["status"].startswith("201")
    assert payload["invitation"]["token"] == "one-time-secret"
    assert payload["invitation"]["invitation_id"] == "invite-1"


def test_invitation_inbox_is_scoped_to_authenticated_recipient_and_never_returns_token():
    app = EnterpriseInvitationHttpMiddleware(lambda e,s: [b"fallback"], Service())
    response = _request(app, "/api/enterprise/invitations/inbox")
    payload = json.loads(response["body"])
    assert response["status"].startswith("200")
    assert payload["contract_version"] == "cubi-team-invitation-inbox.v1"
    assert payload["invitations"][0]["invitation_id"] == "invite-inbox-1"
    assert "token" not in payload["invitations"][0]
