from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from construction_pm.enterprise_organization_access_http import EnterpriseOrganizationAccessHttpMiddleware

NOW = datetime(2026,11,15,tzinfo=timezone.utc)


class Service:
    def list_members(self, session_id, team_id):
        return (type("Membership",(),{"team_id":team_id,"user_id":"member-1","role":"member",
            "status":"active","scope_project_ids":(),"revision":1,"created_at":NOW,
            "revoked_at":None})(),)

    def list_my_teams(self, session_id):
        return (type("Team",(),{"team_id":"team-1","name":"Team","owner_user_id":"owner",
            "status":"active","revision":2,"created_at":NOW,"updated_at":NOW})(),)

    def transfer_ownership(self, session_id, team_id, new_owner_user_id, *, expected_team_revision):
        assert session_id == "session-1"
        assert team_id == "team-1"
        assert expected_team_revision == 2
        return type("Team",(),{"team_id":team_id,"name":"Team","owner_user_id":new_owner_user_id,
            "status":"active","revision":3,"created_at":NOW,"updated_at":NOW})()


def request(app, path, method="GET", body=None, cookie="cp_session=session-1"):
    raw=json.dumps(body or {}).encode()
    environ={"REQUEST_METHOD":method,"PATH_INFO":path,"HTTP_COOKIE":cookie,
             "CONTENT_LENGTH":str(len(raw)),"wsgi.input":io.BytesIO(raw)}
    result={}
    def start(status,headers): result["status"]=status
    result["body"]=b"".join(app(environ,start))
    return result


def test_team_list_requires_session_and_transfer_ownership_is_exposed():
    app=EnterpriseOrganizationAccessHttpMiddleware(lambda e,s:[b"fallback"],Service())
    missing=request(app,"/api/enterprise/teams",cookie="")
    assert missing["status"].startswith("401")
    listed=request(app,"/api/enterprise/teams")
    assert json.loads(listed["body"])["teams"][0]["owner_user_id"]=="owner"
    members=request(app,"/api/enterprise/teams/team-1/members")
    assert json.loads(members["body"])["memberships"][0]["user_id"]=="member-1"
    moved=request(app,"/api/enterprise/teams/team-1/transfer-ownership","POST",{
        "contract_version":"cubi-enterprise-organization-access.v1",
        "new_owner_user_id":"member-1","expected_team_revision":2,
    })
    payload=json.loads(moved["body"])
    assert moved["status"].startswith("200")
    assert payload["team"]["owner_user_id"]=="member-1"
    assert payload["team"]["revision"]==3


def test_invitation_routes_are_delegated_to_invitation_middleware():
    app=EnterpriseOrganizationAccessHttpMiddleware(lambda e,s:[b"invitation-handler"],Service())
    response=request(app,"/api/enterprise/teams/team-1/invitations")
    assert response["body"]==b"invitation-handler"
