import http.client
import json
import sys
import time

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
RUN = str(int(time.time() * 1000))  # keeps every run independent of earlier data


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

s, team = admin.call("POST", "/api/enterprise/teams", {"name": "Live Verify 2"}, key=f"live-team-2-{RUN}")
tid = team.get("record", {}).get("record_id")
check("team create 201", s == 201 and team["record"]["revision"] == 1, f"{s} {team}")

s, d = admin.call("POST", "/api/enterprise/teams", {"name": "Live Verify 2"}, key=f"live-team-2-{RUN}")
check("team idempotent replay same id", s == 201 and d["record"]["record_id"] == tid, s)

s, d = admin.call("POST", "/api/enterprise/teams", {"name": "Other"}, key=f"live-team-2-{RUN}")
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
s, d = admin.call("POST", "/api/enterprise/tasks", {"contract_version": "cubi-enterprise-task.v1", "title": "Live task"}, key=f"live-task-1-{RUN}")
task_id = d.get("task", {}).get("task_id")
check("task create 201", s == 201 and task_id, f"{s} {d}")
s, d = admin.call("PATCH", f"/api/enterprise/tasks/{task_id}", {"contract_version": "cubi-enterprise-task.v1", "expected_revision": 1, "status": "completed"})
check("task complete rev2", s == 200 and d.get("revision") == 2, f"{s} {d}")
s, d = admin.call("PATCH", f"/api/enterprise/tasks/{task_id}", {"contract_version": "cubi-enterprise-task.v1", "expected_revision": 1, "title": "stale"})
check("task stale -> 409", s == 409, f"{s} {d}")

# Approvals
s, d = admin.call("POST", "/api/enterprise/approvals", {"title": "Live approval"}, key=f"live-apv-1-{RUN}")
apid = d.get("record", {}).get("record_id")
check("approval create 201", s == 201 and apid, s)
s, d = admin.call("POST", f"/api/enterprise/approvals/{apid}/decisions", {"expected_revision": 1, "decision": "approve"}, key=f"live-dec-1-{RUN}")
check("approval decision 201", s == 201 and d["decision"]["decision"] == "approve", f"{s} {d}")
s, d = admin.call("GET", f"/api/enterprise/approvals/{apid}")
check("approval status approved rev2", s == 200 and d["record"]["status"] == "approved" and d["record"]["revision"] == 2, s)
s, d = admin.call("POST", f"/api/enterprise/approvals/{apid}/decisions", {"expected_revision": 1, "decision": "approve"}, key=f"live-dec-1-{RUN}")
check("duplicate decision -> 409", s == 409 and d.get("code") == "DUPLICATE_DECISION", f"{s} {d}")
s, d = admin.call("POST", f"/api/enterprise/approvals/{apid}/decisions", {"expected_revision": 1, "decision": "reject"}, key=f"live-dec-2-{RUN}")
check("stale decision -> 409", s == 409 and d.get("code") == "STALE_REVISION", f"{s} {d}")

# Workflow publish validation and versioning
steps = [{"id": "draft", "name": "Draft"}, {"id": "done", "name": "Done", "terminal": True}]
s, d = admin.call("POST", "/api/enterprise/workflows", {"name": "Live flow", "steps": steps, "transitions": []}, key=f"live-wf-1-{RUN}")
wfid = d.get("record", {}).get("record_id")
check("workflow create 201", s == 201 and wfid, s)
s, d = admin.call("POST", f"/api/enterprise/workflows/{wfid}/publish", {"expected_revision": 1})
check("invalid publish -> 400", s == 400 and "unreachable" in d.get("code", ""), f"{s} {d}")
s, d = admin.call("POST", f"/api/enterprise/workflows/{wfid}/publish", {"expected_revision": 1, "transitions": [{"from": "draft", "to": "done"}]})
check("valid publish v1", s == 200 and d["record"]["published_version"] == 1, f"{s} {d}")
s, d = admin.call("POST", f"/api/enterprise/workflows/{wfid}/publish", {"expected_revision": 1, "transitions": [{"from": "draft", "to": "done"}]})
check("stale publish -> 409", s == 409, f"{s} {d}")

# Dashboard persistence
s, d = admin.call("POST", "/api/enterprise/dashboards", {"title": "Live dashboard", "layout": []}, key=f"live-dash-1-{RUN}")
did = d.get("record", {}).get("record_id")
check("dashboard create 201", s == 201 and did, s)
s, d = admin.call("PATCH", f"/api/enterprise/dashboards/{did}", {"expected_revision": 1, "title": "Live dashboard 2"})
check("dashboard update rev2", s == 200 and d["record"]["revision"] == 2, s)

s, d = admin.call("GET", "/api/enterprise/audit")
check("audit read", s == 200 and len(d["items"]) > 0, s)
s, d = admin.call("POST", "/api/enterprise/audit", {})
check("audit read-only", s == 405, s)

# Initial-set registers added with the delivery
s, d = admin.call("POST", "/api/enterprise/risks", {"title": "Live risk", "risk_type": "risk", "severity": "high"}, key=f"live-risk-1-{RUN}")
risk_id = d.get("record", {}).get("record_id")
check("risk create 201", s == 201 and risk_id, f"{s} {d}")
s, d = admin.call("PATCH", f"/api/enterprise/risks/{risk_id}", {"expected_revision": 1, "status": "mitigated"})
check("risk update rev2", s == 200 and d["record"]["revision"] == 2, f"{s} {d}")
s, d = admin.call("DELETE", f"/api/enterprise/risks/{risk_id}", {"expected_revision": 2})
check("risk soft delete", s == 200 and d["record"]["deleted_at"], s)
s, d = admin.call("GET", "/api/enterprise/risks")
check("deleted risk hidden by default", risk_id not in {item["record_id"] for item in d.get("items", [])}, s)
s, d = admin.call("GET", "/api/enterprise/risks?include_deleted=1")
check("deleted risk listed with include_deleted", risk_id in {item["record_id"] for item in d.get("items", [])}, s)
s, d = admin.call("POST", f"/api/enterprise/risks/{risk_id}/restore", {"expected_revision": 3})
check("risk restore", s == 200 and d["record"]["deleted_at"] is None, s)
s, d = admin.call("POST", "/api/enterprise/risks", {"title": "Bad severity", "severity": "extreme"})
check("risk severity validated", s == 400 and d.get("code") == "SEVERITY_INVALID", f"{s} {d}")

s, d = admin.call("POST", "/api/enterprise/timesheets", {"user_id": "preview-planner", "work_date": "2026-11-16", "hours": 26})
check("timesheet hours validated", s == 400 and d.get("code") == "HOURS_INVALID", f"{s} {d}")
s, d = admin.call("POST", "/api/enterprise/timesheets", {"user_id": "preview-planner", "work_date": "2026-11-16", "hours": 7.5})
check("timesheet create 201", s == 201, s)

s, d = admin.call("POST", "/api/enterprise/forms", {"name": "Live form", "fields": [{"name": "title", "type": "text"}]}, key=f"live-form-1-{RUN}")
check("form create 201", s == 201 and d["record"]["fields"][0]["name"] == "title", f"{s} {d}")
s, d = admin.call("POST", "/api/enterprise/forms", {"name": "Empty form", "fields": []})
check("empty form rejected", s == 400 and d.get("code") == "FORM_FIELDS_REQUIRED", f"{s} {d}")

s, d = admin.call("POST", "/api/enterprise/settings", {"key": "timesheet.week_start", "value": "monday"})
check("setting create 201", s == 201, s)

s, d = admin.call("POST", "/api/enterprise/directory", {"display_name": "Live person", "capacity_hours": 40})
check("directory create 201", s == 201, s)

s, d = viewer.call("POST", "/api/enterprise/settings", {"key": "k", "value": "v"})
check("viewer setting write -> 403 admin", s == 403 and d.get("code") == "ENTERPRISE_ADMIN_REQUIRED", f"{s} {d}")
s, d = viewer.call("POST", "/api/enterprise/risks", {"title": "Viewer risk"})
check("viewer risk write -> 403 write", s == 403 and d.get("code") == "ENTERPRISE_WRITE_DENIED", f"{s} {d}")
s, d = viewer.call("GET", "/api/enterprise/audit")
check("viewer audit read -> 403 without an enterprise role", s == 403 and d.get("code") == "ENTERPRISE_ACCESS_DENIED", f"{s} {d}")

for kind in ("portlets", "portfolio", "evm"):
    s, d = admin.call("GET", f"/api/enterprise/{kind}")
    check(f"{kind} -> 503 honest", s == 503 and d.get("code") == "ENGINEERING_SOURCE_NOT_CONNECTED", s)

print()
failed = [r for r in results if not r[1]]
print(f"{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
