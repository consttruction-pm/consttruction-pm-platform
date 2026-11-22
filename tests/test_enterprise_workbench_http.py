from __future__ import annotations

import io
import json
import sqlite3
import unittest
from types import SimpleNamespace

from construction_pm.application.project_lifecycle import SessionError
from construction_pm.enterprise_workbench_http import (
    EnterpriseWorkbenchHttpMiddleware,
    EnterpriseWorkbenchStore,
)


class FakeLifecycle:
    def __init__(self):
        self.sessions = {
            "alice-session": SimpleNamespace(
                user_id="alice", tenant_id="tenant-a", roles=frozenset({"enterprise_admin"})
            ),
            "bob-session": SimpleNamespace(
                user_id="bob", tenant_id="tenant-a", roles=frozenset({"enterprise_viewer"})
            ),
            "carol-session": SimpleNamespace(
                user_id="carol", tenant_id="tenant-b", roles=frozenset({"enterprise_admin"})
            ),
            "dave-session": SimpleNamespace(
                user_id="dave", tenant_id="tenant-a", roles=frozenset({"project_manager"})
            ),
        }

    def get_session(self, session_id, *, now):
        if session_id not in self.sessions:
            raise SessionError("SESSION_INVALID")
        return self.sessions[session_id]


def _request(app, method, path, *, body=None, session="alice-session", headers=None, query=""):
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "HTTP_COOKIE": f"cp_session={session}" if session else "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(app(environ, start_response))
    return captured["status"], json.loads(payload)


class EnterpriseWorkbenchHttpTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.store = EnterpriseWorkbenchStore(self.connection)
        self.store.initialize()
        self.store.seed_preview_fixtures(
            "tenant-a",
            [
                {"user_id": "alice", "display_name": "Alice", "email": None, "roles": ["enterprise_admin"]},
                {"user_id": "bob", "display_name": "Bob", "email": None, "roles": ["enterprise_viewer"]},
            ],
        )
        self.app = EnterpriseWorkbenchHttpMiddleware(
            lambda environ, start: start("404 Not Found", []) or [b"{}"],
            FakeLifecycle(),
            self.store,
        )

    def tearDown(self):
        self.connection.close()

    def _team(self, name="Delivery"):
        return _request(
            self.app,
            "POST",
            "/api/enterprise/teams",
            body={"name": name},
            headers={"Idempotency-Key": f"team-{name}"},
        )

    # -- authentication and authorization ---------------------------------
    def test_unauthenticated_requests_are_rejected(self):
        status, payload = _request(self.app, "GET", "/api/enterprise/teams", session=None)
        self.assertTrue(status.startswith("401"))
        self.assertEqual(payload["code"], "SESSION_REQUIRED")

        status, payload = _request(self.app, "GET", "/api/enterprise/teams", session="expired")
        self.assertTrue(status.startswith("401"))
        self.assertEqual(payload["code"], "SESSION_REQUIRED")

    def test_reader_can_read_but_not_write(self):
        status, payload = _request(self.app, "GET", "/api/enterprise/teams", session="bob-session")
        self.assertTrue(status.startswith("200"))
        self.assertIsInstance(payload["items"], list)

        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/teams",
            body={"name": "Denied"},
            session="bob-session",
        )
        self.assertTrue(status.startswith("403"))
        self.assertEqual(payload["code"], "ENTERPRISE_ADMIN_REQUIRED")

    def test_non_enterprise_role_has_no_access(self):
        status, payload = _request(self.app, "GET", "/api/enterprise/teams", session="dave-session")
        self.assertTrue(status.startswith("403"))
        self.assertEqual(payload["code"], "ENTERPRISE_ACCESS_DENIED")

    def test_admin_kinds_require_enterprise_admin(self):
        self.connection.execute(
            "INSERT INTO enterprise_records (tenant_id, kind, record_id, revision, payload_json, "
            "created_at, updated_at, created_by_user_id) VALUES (?,?,?,?,?,?,?,?)",
            ("tenant-a", "teams", "team-existing", 1, json.dumps({"name": "Existing"}), "2026-01-01T00:00:00+00:00", None, "alice"),
        )
        self.connection.commit()
        # Make bob a contributor (not admin) to prove admin kind separation.
        self.app._lifecycle.sessions["bob-session"].roles = frozenset({"enterprise_user"})
        status, payload = _request(
            self.app,
            "PATCH",
            "/api/enterprise/teams/team-existing",
            body={"expected_revision": 1, "name": "Renamed"},
            session="bob-session",
        )
        self.assertTrue(status.startswith("403"))
        self.assertEqual(payload["code"], "ENTERPRISE_ADMIN_REQUIRED")

    # -- create, read, update, delete, restore ----------------------------
    def test_crud_revisions_and_soft_delete_restore(self):
        status, payload = self._team()
        self.assertTrue(status.startswith("201"))
        record = payload["record"]
        self.assertEqual(record["revision"], 1)
        self.assertEqual(record["status"], "active")
        team_id = record["record_id"]

        status, payload = _request(self.app, "GET", "/api/enterprise/teams")
        self.assertIn(team_id, [item["record_id"] for item in payload["items"]])

        status, payload = _request(
            self.app,
            "PATCH",
            f"/api/enterprise/teams/{team_id}",
            body={"expected_revision": 1, "name": "Delivery 2"},
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["record"]["revision"], 2)
        self.assertEqual(payload["record"]["name"], "Delivery 2")

        status, payload = _request(
            self.app,
            "PATCH",
            f"/api/enterprise/teams/{team_id}",
            body={"expected_revision": 1, "name": "Stale"},
        )
        self.assertTrue(status.startswith("409"))
        self.assertEqual(payload["code"], "REVISION_CONFLICT")

        status, payload = _request(
            self.app,
            "DELETE",
            f"/api/enterprise/teams/{team_id}",
            body={"expected_revision": 2},
        )
        self.assertTrue(status.startswith("200"))
        self.assertIsNotNone(payload["record"]["deleted_at"])
        self.assertEqual(payload["record"]["revision"], 3)

        status, payload = _request(self.app, "GET", f"/api/enterprise/teams/{team_id}")
        self.assertTrue(status.startswith("404"))

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/teams/{team_id}/restore",
            body={"expected_revision": 3},
        )
        self.assertTrue(status.startswith("200"))
        self.assertIsNone(payload["record"]["deleted_at"])
        self.assertEqual(payload["record"]["revision"], 4)

        status, payload = _request(self.app, "GET", f"/api/enterprise/teams/{team_id}")
        self.assertTrue(status.startswith("200"))

    def test_restore_requires_a_deleted_record(self):
        _, payload = self._team("Restore")
        team_id = payload["record"]["record_id"]
        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/teams/{team_id}/restore",
            body={"expected_revision": 1},
        )
        self.assertTrue(status.startswith("409"))
        self.assertEqual(payload["code"], "RECORD_NOT_DELETED")

    def test_tenant_isolation_prevents_cross_tenant_reads(self):
        _, payload = self._team("Isolated")
        team_id = payload["record"]["record_id"]

        status, payload = _request(self.app, "GET", "/api/enterprise/teams", session="carol-session")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["items"], [])

        status, payload = _request(
            self.app, "GET", f"/api/enterprise/teams/{team_id}", session="carol-session"
        )
        self.assertTrue(status.startswith("404"))
        self.assertEqual(payload["code"], "ENTERPRISE_RECORD_NOT_FOUND")

        status, payload = _request(
            self.app,
            "GET",
            "/api/enterprise/teams",
            session="carol-session",
            query="tenant_id=tenant-a",
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["items"], [])

    def test_client_supplied_tenant_is_rejected(self):
        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/teams",
            body={"name": "Spoof", "tenant_id": "tenant-b"},
        )
        self.assertTrue(status.startswith("403"))
        self.assertEqual(payload["code"], "TENANT_IS_CLIENT_CONTROLLED")

    def test_create_is_idempotent_and_rejects_key_reuse_with_new_payload(self):
        status, first = self._team("Idem")
        self.assertTrue(status.startswith("201"))
        team_id = first["record"]["record_id"]

        status, second = _request(
            self.app,
            "POST",
            "/api/enterprise/teams",
            body={"name": "Idem"},
            headers={"Idempotency-Key": "team-Idem"},
        )
        self.assertTrue(status.startswith("201"))
        self.assertEqual(second["record"]["record_id"], team_id)
        self.assertEqual(second["record"]["revision"], 1)

        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/teams",
            body={"name": "Different"},
            headers={"Idempotency-Key": "team-Idem"},
        )
        self.assertTrue(status.startswith("409"))
        self.assertEqual(payload["code"], "IDEMPOTENCY_KEY_REUSE")

    def test_required_fields_and_membership_role_are_validated(self):
        status, payload = _request(self.app, "POST", "/api/enterprise/workflows", body={"name": "No steps"})
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "STEPS_REQUIRED")

        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/memberships",
            body={"team_id": "team-preview-delivery", "user_id": "alice", "role": "owner!"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "MEMBERSHIP_ROLE_INVALID")

        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/invitations",
            body={"email": "not-an-email", "role": "member"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "EMAIL_INVALID")

        # A record form submits untouched optional fields as ""; that is
        # "not provided", not an invalid address.
        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/directory",
            body={"display_name": "Blank email", "email": "", "role_title": "Planner"},
        )
        self.assertTrue(status.startswith("201"), f"{status} {payload}")
        self.assertEqual(payload["record"]["display_name"], "Blank email")
        self.assertEqual(payload["record"]["email"], "")

    def test_immutable_fields_cannot_be_patched(self):
        _, payload = self._team("Immutable")
        team_id = payload["record"]["record_id"]
        status, payload = _request(
            self.app,
            "PATCH",
            f"/api/enterprise/teams/{team_id}",
            body={"expected_revision": 1, "record_id": "other"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "IMMUTABLE_FIELDS")

    # -- approvals --------------------------------------------------------
    def _approval(self):
        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/approvals",
            body={"title": "Approve baseline"},
            headers={"Idempotency-Key": "approval-create-1"},
        )
        self.assertTrue(status.startswith("201"))
        return payload["record"]["record_id"]

    def test_approval_decision_updates_status_and_rejects_duplicates_and_stale(self):
        approval_id = self._approval()

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/approvals/{approval_id}/decisions",
            body={"expected_revision": 1, "decision": "approve", "comment": "ok"},
            headers={"Idempotency-Key": "decision-1"},
        )
        self.assertTrue(status.startswith("201"))
        self.assertEqual(payload["decision"]["decision"], "approve")
        decision_id = payload["decision"]["decision_id"]

        status, payload = _request(self.app, "GET", f"/api/enterprise/approvals/{approval_id}")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["record"]["status"], "approved")
        self.assertEqual(payload["record"]["revision"], 2)

        status, payload = _request(
            self.app,
            "GET",
            f"/api/enterprise/approvals/{approval_id}/decisions",
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual([item["decision_id"] for item in payload["items"]], [decision_id])

        # The same one-shot key is rejected even with an identical payload.
        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/approvals/{approval_id}/decisions",
            body={"expected_revision": 1, "decision": "approve", "comment": "ok"},
            headers={"Idempotency-Key": "decision-1"},
        )
        self.assertTrue(status.startswith("409"))
        self.assertEqual(payload["code"], "DUPLICATE_DECISION")

        # A fresh key with an outdated revision is also rejected.
        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/approvals/{approval_id}/decisions",
            body={"expected_revision": 1, "decision": "reject"},
            headers={"Idempotency-Key": "decision-2"},
        )
        self.assertTrue(status.startswith("409"))
        self.assertEqual(payload["code"], "STALE_REVISION")

    def test_approval_decision_requires_idempotency_key_and_valid_decision(self):
        approval_id = self._approval()

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/approvals/{approval_id}/decisions",
            body={"expected_revision": 1, "decision": "approve"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "IDEMPOTENCY_KEY_REQUIRED")

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/approvals/{approval_id}/decisions",
            body={"decision": "approve"},
            headers={"Idempotency-Key": "decision-3"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "EXPECTED_REVISION_REQUIRED")

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/approvals/{approval_id}/decisions",
            body={"expected_revision": 1, "decision": "maybe"},
            headers={"Idempotency-Key": "decision-4"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "DECISION_INVALID")

    # -- workflows --------------------------------------------------------
    def test_workflow_publish_validates_graph_and_versions(self):
        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/workflows",
            body={
                "name": "Review",
                "steps": [
                    {"id": "draft", "name": "Draft"},
                    {"id": "approved", "name": "Approved", "terminal": True},
                ],
                "transitions": [],
            },
            headers={"Idempotency-Key": "workflow-1"},
        )
        self.assertTrue(status.startswith("201"))
        workflow_id = payload["record"]["record_id"]

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/workflows/{workflow_id}/publish",
            body={"expected_revision": 1},
        )
        self.assertTrue(status.startswith("400"))
        self.assertIn("unreachable", payload["code"])

        steps = [
            {"id": "draft", "name": "Draft"},
            {"id": "approved", "name": "Approved", "terminal": True},
        ]
        transitions = [{"from": "draft", "to": "approved"}]

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/workflows/{workflow_id}/publish",
            body={"expected_revision": 1, "steps": steps, "transitions": transitions},
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["record"]["status"], "published")
        self.assertEqual(payload["record"]["published_version"], 1)
        self.assertEqual(payload["record"]["revision"], 2)

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/workflows/{workflow_id}/publish",
            body={"expected_revision": 1, "steps": steps, "transitions": transitions},
        )
        self.assertTrue(status.startswith("409"))
        self.assertEqual(payload["code"], "REVISION_CONFLICT")

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/workflows/{workflow_id}/publish",
            body={"expected_revision": 2, "steps": steps, "transitions": transitions},
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["record"]["published_version"], 2)

    def test_workflow_rejects_self_loop_duplicate_and_missing_transitions(self):
        status, payload = _request(
            self.app,
            "POST",
            "/api/enterprise/workflows",
            body={
                "name": "Broken",
                "steps": [
                    {"id": "a", "name": "A"},
                    {"id": "b", "name": "B", "terminal": True},
                ],
                "transitions": [
                    {"from": "a", "to": "a"},
                    {"from": "a", "to": "b"},
                    {"from": "a", "to": "b"},
                    {"from": "b", "to": "missing"},
                ],
            },
            headers={"Idempotency-Key": "workflow-broken"},
        )
        self.assertTrue(status.startswith("201"))
        workflow_id = payload["record"]["record_id"]

        status, payload = _request(
            self.app,
            "POST",
            f"/api/enterprise/workflows/{workflow_id}/publish",
            body={"expected_revision": 1},
        )
        self.assertTrue(status.startswith("400"))
        self.assertTrue(payload["code"].startswith("WORKFLOW_INVALID:"))
        self.assertIn("itself", payload["code"])
        self.assertIn("duplicate", payload["code"])
        self.assertIn("missing step", payload["code"])

    # -- audit and unsupported routes ------------------------------------
    def test_audit_records_writes_and_is_read_only(self):
        _, payload = self._team("Audited")
        team_id = payload["record"]["record_id"]
        _request(
            self.app,
            "PATCH",
            f"/api/enterprise/teams/{team_id}",
            body={"expected_revision": 1, "name": "Audited 2"},
        )
        _request(self.app, "DELETE", f"/api/enterprise/teams/{team_id}", body={"expected_revision": 2})
        _request(
            self.app,
            "POST",
            f"/api/enterprise/teams/{team_id}/restore",
            body={"expected_revision": 3},
        )

        status, payload = _request(self.app, "GET", "/api/enterprise/audit")
        self.assertTrue(status.startswith("200"))
        actions = {item["action"] for item in payload["items"]}
        self.assertTrue({"create", "update", "delete", "restore"} <= actions)
        self.assertTrue(all(item["actor_id"] == "alice" for item in payload["items"]))

        status, payload = _request(self.app, "POST", "/api/enterprise/audit", body={})
        self.assertTrue(status.startswith("405"))
        self.assertEqual(payload["code"], "METHOD_NOT_ALLOWED")

    def test_engineering_derived_routes_are_not_fabricated(self):
        for kind in ("portlets", "portfolio", "evm"):
            status, payload = _request(self.app, "GET", f"/api/enterprise/{kind}")
            self.assertTrue(status.startswith("503"), kind)
            self.assertEqual(payload["code"], "ENGINEERING_SOURCE_NOT_CONNECTED")

        status, payload = _request(self.app, "GET", "/api/enterprise/unknown-kind")
        self.assertTrue(status.startswith("404"))
        self.assertEqual(payload["code"], "ROUTE_NOT_FOUND")

    def test_task_routes_are_left_to_the_task_middleware(self):
        status, payload = _request(self.app, "GET", "/api/enterprise/tasks")
        self.assertTrue(status.startswith("404"))
        self.assertEqual(payload, {})  # The inner app answered, not this middleware.

    # -- register kinds delivered with the initial-set pages --------------
    REGISTER_PAYLOADS = {
        "risks": {"title": "Excavation collapse", "risk_type": "risk", "severity": "high", "owner": "alice"},
        "documents": {"title": "Method statement", "category": "procedure", "owner": "alice"},
        "eps": {"name": "North region", "code": "NR", "parent_id": ""},
        "timesheets": {"user_id": "alice", "work_date": "2026-11-16", "hours": 7.5},
        "notifications": {"title": "Review due", "audience": "team-preview-delivery", "channel": "in_app"},
        "settings": {"key": "timesheet.week_start", "value": "monday"},
        "forms": {"name": "Site observation", "fields": [{"name": "title", "type": "text"}]},
        "directory": {"display_name": "Alice", "role_title": "Planner", "capacity_hours": 40},
    }

    def test_register_kinds_support_full_crud_and_restore(self):
        for kind, payload in self.REGISTER_PAYLOADS.items():
            with self.subTest(kind=kind):
                status, created = _request(self.app, "POST", f"/api/enterprise/{kind}", body=payload)
                self.assertTrue(status.startswith("201"), (kind, status, created))
                record = created["record"]
                self.assertEqual(record["kind"], kind)
                self.assertEqual(record["revision"], 1)

                status, listed = _request(self.app, "GET", f"/api/enterprise/{kind}")
                self.assertTrue(status.startswith("200"))
                self.assertIn(record["record_id"], {item["record_id"] for item in listed["items"]})

                status, updated = _request(
                    self.app,
                    "PATCH",
                    f"/api/enterprise/{kind}/{record['record_id']}",
                    body={"expected_revision": 1, "status": "archived"},
                )
                self.assertTrue(status.startswith("200"), (kind, status, updated))
                self.assertEqual(updated["record"]["revision"], 2)
                self.assertEqual(updated["record"]["status"], "archived")

                status, deleted = _request(
                    self.app,
                    "DELETE",
                    f"/api/enterprise/{kind}/{record['record_id']}",
                    body={"expected_revision": 2},
                )
                self.assertTrue(status.startswith("200"))
                self.assertIsNotNone(deleted["record"]["deleted_at"])

                status, hidden = _request(self.app, "GET", f"/api/enterprise/{kind}")
                self.assertNotIn(record["record_id"], {item["record_id"] for item in hidden["items"]})

                status, with_deleted = _request(
                    self.app, "GET", f"/api/enterprise/{kind}", query="include_deleted=1"
                )
                self.assertIn(record["record_id"], {item["record_id"] for item in with_deleted["items"]})

                status, restored = _request(
                    self.app,
                    "POST",
                    f"/api/enterprise/{kind}/{record['record_id']}/restore",
                    body={"expected_revision": 3},
                )
                self.assertTrue(status.startswith("200"))
                self.assertIsNone(restored["record"]["deleted_at"])

    def test_register_records_are_tenant_isolated(self):
        _, created = _request(self.app, "POST", "/api/enterprise/risks", body={"title": "Tenant A risk"})
        risk_id = created["record"]["record_id"]
        status, _ = _request(self.app, "GET", f"/api/enterprise/risks/{risk_id}", session="carol-session")
        self.assertTrue(status.startswith("404"))
        status, payload = _request(self.app, "GET", "/api/enterprise/risks", session="carol-session")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(payload["items"], [])

    def test_timesheet_hours_and_date_are_validated(self):
        for body, code in (
            ({"user_id": "alice", "work_date": "2026-11-16", "hours": 0}, "HOURS_INVALID"),
            ({"user_id": "alice", "work_date": "2026-11-16", "hours": 25}, "HOURS_INVALID"),
            ({"user_id": "alice", "work_date": "2026-11-16", "hours": "8"}, "HOURS_INVALID"),
            ({"user_id": "alice", "work_date": "16/11/2026", "hours": 8}, "WORK_DATE_INVALID"),
            ({"user_id": "alice", "work_date": "2026-02-30", "hours": 8}, "WORK_DATE_INVALID"),
        ):
            with self.subTest(code=code):
                status, payload = _request(self.app, "POST", "/api/enterprise/timesheets", body=body)
                self.assertTrue(status.startswith("400"))
                self.assertEqual(payload["code"], code)

        _, created = _request(
            self.app, "POST", "/api/enterprise/timesheets",
            body={"user_id": "alice", "work_date": "2026-11-16", "hours": 8},
        )
        record = created["record"]
        status, payload = _request(
            self.app,
            "PATCH",
            f"/api/enterprise/timesheets/{record['record_id']}",
            body={"expected_revision": 1, "hours": 30},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "HOURS_INVALID")

    def test_risk_type_and_severity_are_validated(self):
        status, payload = _request(
            self.app, "POST", "/api/enterprise/risks",
            body={"title": "Bad type", "risk_type": "hazard"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "RISK_TYPE_INVALID")
        status, payload = _request(
            self.app, "POST", "/api/enterprise/risks",
            body={"title": "Bad severity", "severity": "extreme"},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "SEVERITY_INVALID")

    def test_forms_require_named_fields(self):
        status, payload = _request(
            self.app, "POST", "/api/enterprise/forms", body={"name": "Empty"}
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "FIELDS_REQUIRED")

        status, payload = _request(
            self.app, "POST", "/api/enterprise/forms",
            body={"name": "Unnamed", "fields": [{"type": "text"}]},
        )
        self.assertTrue(status.startswith("400"))
        self.assertEqual(payload["code"], "FORM_FIELD_INVALID")

    def test_admin_register_kinds_reject_non_admins_but_stay_readable(self):
        for kind in ("settings", "forms"):
            with self.subTest(kind=kind):
                status, payload = _request(
                    self.app, "POST", f"/api/enterprise/{kind}",
                    body={"key": "k", "value": "v", "name": "n", "fields": [{"name": "f"}]},
                    session="dave-session",
                )
                self.assertTrue(status.startswith("403"))
                self.assertEqual(payload["code"], "ENTERPRISE_ADMIN_REQUIRED")

                status, payload = _request(
                    self.app, "GET", f"/api/enterprise/{kind}", session="bob-session"
                )
                self.assertTrue(status.startswith("200"))
                self.assertEqual(payload["items"], [])

    def test_non_admin_registers_reject_viewers(self):
        status, payload = _request(
            self.app, "POST", "/api/enterprise/risks", body={"title": "Viewer write"}, session="bob-session"
        )
        self.assertTrue(status.startswith("403"))
        self.assertEqual(payload["code"], "ENTERPRISE_WRITE_DENIED")

    def test_seed_is_idempotent(self):
        before = len(self.store.list("tenant-a", "teams"))
        self.store.seed_preview_fixtures(
            "tenant-a", [{"user_id": "alice", "display_name": "Alice"}]
        )
        self.assertEqual(len(self.store.list("tenant-a", "teams")), before)


if __name__ == "__main__":
    unittest.main()
