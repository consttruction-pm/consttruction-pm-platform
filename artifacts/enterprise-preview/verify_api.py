import http.client
import json
import sys

HOST, PORT = "127.0.0.1", 4180


def login(role="enterprise"):
    conn = http.client.HTTPConnection(HOST, PORT)
    body = f"role={role}&next=/cubi/"
    conn.request("POST", "/preview/login", body, {"Content-Type": "application/x-www-form-urlencoded"})
    resp = conn.getresponse()
    resp.read()
    cookie = resp.getheader("Set-Cookie", "").split(";")[0]
    conn.close()
    return cookie


class Client:
    def __init__(self, cookie):
        self.cookie = cookie

    def call(self, method, path, body=None, key=None, headers=None):
        conn = http.client.HTTPConnection(HOST, PORT)
        hdrs = {"Cookie": self.cookie, "Content-Type": "application/json"}
        if key:
            hdrs["Idempotency-Key"] = key
        hdrs.update(headers or {})
        payload = None if body is None else json.dumps(body)
        conn.request(method, path, payload, hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        status = resp.status
        conn.close()
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"_raw": raw[:200]}
        return status, data


results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    print(("PASS " if condition else "FAIL ") + name + (" :: " + str(detail) if detail else ""))


admin = Client(login("enterprise"))
viewer = Client(login("viewer"))
anon = Client("")

s, d = anon.call("GET", "/api/enterprise/teams")
check("anonymous teams -> 401", s == 401 and d.get("code") == "SESSION_REQUIRED", f"{s} {d}")

s, d = viewer.call("GET", "/api/enterprise/teams")
check("non-enterprise role -> 403", s == 403 and d.get("code") == "ENTERPRISE_ACCESS_DENIED", f"{s} {d}")

s, d = admin.call("GET", "/api/enterprise/teams")
check("teams list 200", s == 200 and any(i["record_id"] == "team-preview-delivery" for i in d["items"]), s)

s, team = admin.call("POST", "/api/enterprise/teams", {"name": "Live Verify 2"}, key="live-team-2")
tid = team.get("record", {}).get("record_id")
check("team create 201", s == 201 and team["record"]["revision"] == 1, f"{s} {team}")

s, d = admin.call("POST", "/api/enterprise/teams", {"name": "Live Verify 2"}, key="live-team-2")
check("team idempotent replay same id", s == 201 and d["record"]["record_id"] == tid, s)

s, d = admin.call("POST", "/api/enterprise/teams", {"name": "Other"}, key="live-team-2")
check("team key reuse -> 409", s == 409 and d.get("code") == "IDEMPOTENCY_KEY_REUSE", f"{s} {d}")

s, d = admin.call("POST", "/api/enterprise/teams", {"name": "Spoof", "tenant_id": "x"})
check("client tenant rejected", s == 403 and d.get("code") == "TENANT_IS_CLIENT_CONTROLLED", f"{s} {d}")

s, d = admin.call("PATCH", f"/api/enterprise/teams/{tid}", {"expected_revision": 1, "name": "Live Verify 2b"})
check("team update rev2", s == 200 and d["record"]["revision"] == 2, s)

s, d = admin.call("PATCH", f"/api/enterprise/teams/{tid}", {"expected_revision": 1, "name": "stale"})
check("team stale patch -> 409", s == 409 and d.get("code") == "REVISION_CONFLICT", f"{s} {d}")

s, d = admin.call("DELETE", f"/api/enterprise/teams/{tid}", {"expected_revision": 2})
check("team delete soft", s == 200 and d["record"]["deleted_at"], s)

s, d = admin.call("GET", f"/api/enterprise/teams/{tid}")
check("deleted team hidden", s == 404, s)

s, d = admin.call("POST", f"/api/enterprise/teams/{tid}/restore", {"expected_revision": 3})
check("team restore rev4", s == 200 and d["record"]["revision"] == 4, s)

s, d = admin.call("GET", f"/api/enterprise/teams/{tid}")
check("restored team visible", s == 200, s)

# Tasks via the mature task middleware
s, d = admin.call("GET", "/api/enterprise/tasks")
check("tasks list 200", s == 200, s)
s, d = admin.call("POST", "/api/enterprise/tasks", {"contract_version": "cubi-enterprise-task.v1", "title": "Live task"}, key="live-task-1")
task_id = d.get("task", {}).get("task_id")
check("task create 201", s == 201 and task_id, f"{s} {d}")
s, d = admin.call("PATCH", f"/api/enterprise/tasks/{task_id}", {"contract_version": "cubi-enterprise-task.v1", "expected_revision": 1, "status": "completed"})
check("task complete rev2", s == 200 and d.get("revision") == 2, f"{s} {d}")
s, d = admin.call("PATCH", f"/api/enterprise/tasks/{task_id}", {"contract_version": "cubi-enterprise-task.v1", "expected_revision": 1, "title": "stale"})
check("task stale -> 409", s == 409, f"{s} {d}")

# Approvals
s, d = admin.call("POST", "/api/enterprise/approvals", {"title": "Live approval"}, key="live-apv-1")
apid = d.get("record", {}).get("record_id")
check("approval create 201", s == 201 and apid, s)
s, d = admin.call("POST", f"/api/enterprise/approvals/{apid}/decisions", {"expected_revision": 1, "decision": "approve"}, key="live-dec-1")
check("approval decision 201", s == 201 and d["decision"]["decision"] == "approve", f"{s} {d}")
s, d = admin.call("GET", f"/api/enterprise/approvals/{apid}")
check("approval status approved rev2", s == 200 and d["record"]["status"] == "approved" and d["record"]["revision"] == 2, s)
s, d = admin.call("POST", f"/api/enterprise/approvals/{apid}/decisions", {"expected_revision": 1, "decision": "approve"}, key="live-dec-1")
check("duplicate decision -> 409", s == 409 and d.get("code") == "DUPLICATE_DECISION", f"{s} {d}")
s, d = admin.call("POST", f"/api/enterprise/approvals/{apid}/decisions", {"expected_revision": 1, "decision": "reject"}, key="live-dec-2")
check("stale decision -> 409", s == 409 and d.get("code") == "STALE_REVISION", f"{s} {d}")

# Workflow publish validation and versioning
steps = [{"id": "draft", "name": "Draft"}, {"id": "done", "name": "Done", "terminal": True}]
s, d = admin.call("POST", "/api/enterprise/workflows", {"name": "Live flow", "steps": steps, "transitions": []}, key="live-wf-1")
wfid = d.get("record", {}).get("record_id")
check("workflow create 201", s == 201 and wfid, s)
s, d = admin.call("POST", f"/api/enterprise/workflows/{wfid}/publish", {"expected_revision": 1})
check("invalid publish -> 400", s == 400 and "unreachable" in d.get("code", ""), f"{s} {d}")
s, d = admin.call("POST", f"/api/enterprise/workflows/{wfid}/publish", {"expected_revision": 1, "transitions": [{"from": "draft", "to": "done"}]})
check("valid publish v1", s == 200 and d["record"]["published_version"] == 1, f"{s} {d}")
s, d = admin.call("POST", f"/api/enterprise/workflows/{wfid}/publish", {"expected_revision": 1, "transitions": [{"from": "draft", "to": "done"}]})
check("stale publish -> 409", s == 409, f"{s} {d}")

# Dashboard persistence
s, d = admin.call("POST", "/api/enterprise/dashboards", {"title": "Live dashboard", "layout": []}, key="live-dash-1")
did = d.get("record", {}).get("record_id")
check("dashboard create 201", s == 201 and did, s)
s, d = admin.call("PATCH", f"/api/enterprise/dashboards/{did}", {"expected_revision": 1, "title": "Live dashboard 2"})
check("dashboard update rev2", s == 200 and d["record"]["revision"] == 2, s)

s, d = admin.call("GET", "/api/enterprise/audit")
check("audit read", s == 200 and len(d["items"]) > 0, s)
s, d = admin.call("POST", "/api/enterprise/audit", {})
check("audit read-only", s == 405, s)

for kind in ("portlets", "portfolio", "evm"):
    s, d = admin.call("GET", f"/api/enterprise/{kind}")
    check(f"{kind} -> 503 honest", s == 503 and d.get("code") == "ENGINEERING_SOURCE_NOT_CONNECTED", s)

print()
failed = [r for r in results if not r[1]]
print(f"{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
