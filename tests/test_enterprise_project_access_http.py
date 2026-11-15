from __future__ import annotations

import io
import json

from construction_pm.enterprise_project_access_http import EnterpriseProjectAccessHttpMiddleware


class Service:
    def list_profiles(self, session_id):
        return (type("Profile",(),{"profile_id":"read_only","name":"Read only",
            "permissions":("project.read",),"active":True,"revision":1})(),)

    def list_obs_nodes(self, session_id):
        return (type("OBSNode",(),{"obs_id":"root","parent_obs_id":None,"code":"ROOT",
            "name":"Root","manager_user_id":"admin","sequence_number":1})(),)

    def list_privilege_definitions(self, session_id):
        return (type("Privilege",(),{"key":"activity.view","group":type("Group",(),{"value":"activities"})(),
            "label":"View Activities","description":"View activity data."})(),)


def request(app,path,method="GET",body=None,cookie="cp_session=session-1"):
    raw=json.dumps(body or {}).encode()
    environ={"REQUEST_METHOD":method,"PATH_INFO":path,"HTTP_COOKIE":cookie,
             "CONTENT_LENGTH":str(len(raw)),"wsgi.input":io.BytesIO(raw)}
    result={}
    def start(status,headers): result["status"]=status
    result["body"]=b"".join(app(environ,start))
    return result


def test_profile_and_obs_directory_routes_are_scoped_to_admin_service():
    app=EnterpriseProjectAccessHttpMiddleware(lambda e,s:[b"fallback"],Service())
    profiles=request(app,"/api/enterprise/project-security-profiles")
    assert profiles["status"].startswith("200")
    assert json.loads(profiles["body"])["profiles"][0]["profile_id"]=="read_only"
    obs=request(app,"/api/enterprise/obs")
    assert obs["status"].startswith("200")
    assert json.loads(obs["body"])["obs_nodes"][0]["obs_id"]=="root"


def test_project_access_routes_require_authenticated_session():
    app=EnterpriseProjectAccessHttpMiddleware(lambda e,s:[b"fallback"],Service())
    response=request(app,"/api/enterprise/obs",cookie="")
    assert response["status"].startswith("401")


def test_granular_project_privilege_catalogue_route_returns_grouped_definitions():
    app=EnterpriseProjectAccessHttpMiddleware(lambda e,s:[b"fallback"],Service())
    response=request(app,"/api/enterprise/project-security-privileges")
    assert response["status"].startswith("200")
    payload=json.loads(response["body"])
    assert payload["privileges"][0]["key"]=="activity.view"
    assert payload["privileges"][0]["group"]=="activities"
