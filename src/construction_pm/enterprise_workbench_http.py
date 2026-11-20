"""Tenant-scoped Enterprise Workbench HTTP surface for the local preview.

The production runtime owns dedicated PostgreSQL repositories for dashboards
and organization access. The preview does not have those databases, so this
module provides the same externally observable contract on SQLite:

* identity, tenant and roles always come from the authenticated server session;
* every write is revision-checked, idempotency-aware and audit-recorded;
* records are soft deleted and can be restored;
* collection reads never accept a client-supplied tenant.

It intentionally does not calculate Engineering facts. Portlet, indicator and
trend routes report ``ENGINEERING_SOURCE_NOT_CONNECTED`` until a versioned
source route exists. This is a preview adapter, not a production concurrency
implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import traceback
from datetime import datetime, timezone
from typing import Callable, Mapping, Sequence
from urllib.parse import parse_qs, unquote
from uuid import uuid4

from .application.project_lifecycle import ProjectLifecycleError, SessionError

ENTERPRISE_READ_ROLES = frozenset({"enterprise_viewer", "enterprise_user", "enterprise_admin"})
ENTERPRISE_WRITE_ROLES = frozenset({"enterprise_user", "enterprise_admin"})
ENTERPRISE_ADMIN_ROLES = frozenset({"enterprise_admin"})

_KINDS = {
    "organizations",
    "users",
    "teams",
    "memberships",
    "invitations",
    "roles",
    "grants",
    "workflows",
    "approvals",
    "feedback",
    "portfolios",
    "decisions",
    "dashboards",
}
_ADMIN_KINDS = {"organizations", "users", "teams", "memberships", "invitations", "roles", "grants"}
_IMMUTABLE_FIELDS = {"record_id", "tenant_id", "kind", "created_at", "created_by_user_id", "revision"}
_REQUIRED_FIELDS = {
    "organizations": ("name",),
    "users": ("display_name",),
    "teams": ("name",),
    "memberships": ("team_id", "user_id", "role"),
    "invitations": ("email", "role"),
    "roles": ("name", "scope"),
    "grants": ("subject_id", "resource_id", "role"),
    "workflows": ("name", "steps"),
    "approvals": ("title",),
    "feedback": ("title",),
    "portfolios": ("name",),
    "decisions": ("title",),
    "dashboards": ("title",),
}
_ID_PREFIX = {
    "organizations": "org",
    "users": "usr",
    "teams": "team",
    "memberships": "mem",
    "invitations": "inv",
    "roles": "role",
    "grants": "grant",
    "workflows": "wf",
    "approvals": "apv",
    "feedback": "fb",
    "portfolios": "pf",
    "decisions": "dec",
    "dashboards": "dash",
}


class EnterpriseApiError(ValueError):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class EnterpriseWorkbenchStore:
    """SQLite record store with revisions, soft delete, audit and idempotency."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS enterprise_records (
                tenant_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                record_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                created_by_user_id TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (tenant_id, kind, record_id)
            );
            CREATE TABLE IF NOT EXISTS enterprise_idempotency (
                tenant_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                record_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                PRIMARY KEY (tenant_id, operation, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS enterprise_audit (
                tenant_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                target_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                detail_json TEXT NOT NULL,
                PRIMARY KEY (tenant_id, event_id)
            );
            CREATE TABLE IF NOT EXISTS enterprise_approval_decisions (
                tenant_id TEXT NOT NULL,
                approval_id TEXT NOT NULL,
                decision_id TEXT NOT NULL,
                expected_revision INTEGER NOT NULL,
                decision TEXT NOT NULL,
                comment TEXT,
                actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, approval_id, decision_id)
            );
            """
        )
        self.connection.commit()

    def seed_preview_fixtures(self, tenant_id: str, users: Sequence[Mapping[str, object]]) -> None:
        """Seed static access catalogue and identity rows once.

        Only tenant identity, the role catalogue and a starter team are seeded.
        Tasks, approvals, workflows, invitations and grants stay empty so the
        operator exercises real writes rather than reading sample work items.
        """
        existing = self.connection.execute(
            "SELECT COUNT(*) FROM enterprise_records WHERE tenant_id=?",
            (tenant_id,),
        ).fetchone()
        if existing is not None and int(existing[0]) > 0:
            return
        now = _iso(_now())
        actor = str(users[0]["user_id"]) if users else "preview-admin"
        rows: list[tuple[str, str, str, dict[str, object]]] = []
        rows.append(
            (
                "organizations",
                f"org-{hashlib.sha256(tenant_id.encode()).hexdigest()[:12]}",
                "CUBI Preview Organization",
                {"name": "CUBI Preview Organization", "kind": "tenant", "status": "active", "demo": True},
            )
        )
        for user in users:
            rows.append(
                (
                    "users",
                    f"usr-{str(user['user_id'])}",
                    str(user.get("display_name") or user["user_id"]),
                    {
                        "display_name": str(user.get("display_name") or user["user_id"]),
                        "email": user.get("email"),
                        "user_id": str(user["user_id"]),
                        "roles": list(user.get("roles") or ()),
                        "status": "active",
                        "demo": True,
                    },
                )
            )
        for role_id, name, scope, permissions in (
            ("enterprise_viewer", "Enterprise viewer", "tenant_read", ["read"]),
            ("enterprise_user", "Enterprise user", "tenant_contribute", ["read", "write"]),
            ("enterprise_admin", "Enterprise administrator", "tenant_admin", ["read", "write", "admin"]),
        ):
            rows.append(
                (
                    "roles",
                    f"role-{role_id}",
                    name,
                    {"name": name, "role_id": role_id, "scope": scope, "permissions": permissions, "status": "active", "demo": True},
                )
            )
        rows.append(
            (
                "teams",
                "team-preview-delivery",
                "Preview Delivery",
                {"name": "Preview Delivery", "status": "active", "demo": True},
            )
        )
        for kind, record_id, _label, payload in rows:
            self.connection.execute(
                "INSERT OR IGNORE INTO enterprise_records "
                "(tenant_id, kind, record_id, revision, payload_json, created_at, updated_at, created_by_user_id) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (tenant_id, kind, record_id, 1, json.dumps(payload, sort_keys=True, ensure_ascii=False), now, None, actor),
            )
        self._audit(tenant_id, actor, "seed", "organizations", tenant_id, detail={"demo": True})
        self.connection.commit()

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _fingerprint(payload: Mapping[str, object], kind: str) -> str:
        body = {key: value for key, value in payload.items() if key not in {"record_id", "revision", "created_at", "updated_at"}}
        return hashlib.sha256(
            json.dumps({"kind": kind, "payload": body}, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def _audit(
        self,
        tenant_id: str,
        actor_id: str,
        action: str,
        kind: str,
        record_id: str,
        decision: str = "allowed",
        detail: Mapping[str, object] | None = None,
    ) -> None:
        self.connection.execute(
            "INSERT INTO enterprise_audit "
            "(tenant_id, event_id, actor_id, action, target_kind, target_id, decision, occurred_at, detail_json) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                tenant_id,
                f"evt-{uuid4().hex}",
                actor_id,
                action,
                kind,
                record_id,
                decision,
                _iso(_now()),
                json.dumps(detail or {}, sort_keys=True, ensure_ascii=False),
            ),
        )

    @staticmethod
    def _row(row: tuple) -> dict[str, object]:
        payload = json.loads(row[4])
        payload["tenant_id"] = row[0]
        payload["kind"] = row[1]
        payload["record_id"] = row[2]
        payload["revision"] = int(row[3])
        payload["created_at"] = row[5]
        payload["updated_at"] = row[6]
        payload["created_by_user_id"] = row[7]
        payload["deleted_at"] = row[8]
        return payload

    def get(self, tenant_id: str, kind: str, record_id: str, *, include_deleted: bool = False) -> dict[str, object]:
        row = self.connection.execute(
            "SELECT tenant_id, kind, record_id, revision, payload_json, created_at, updated_at, "
            "created_by_user_id, deleted_at FROM enterprise_records "
            "WHERE tenant_id=? AND kind=? AND record_id=?",
            (tenant_id, kind, record_id),
        ).fetchone()
        if row is None:
            raise EnterpriseApiError(404, "ENTERPRISE_RECORD_NOT_FOUND")
        if row[8] is not None and not include_deleted:
            raise EnterpriseApiError(404, "ENTERPRISE_RECORD_NOT_FOUND")
        return self._row(row)

    def list(
        self,
        tenant_id: str,
        kind: str,
        *,
        status: str | None = None,
        project_id: str | None = None,
        search: str | None = None,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> tuple[dict[str, object], ...]:
        clauses = ["tenant_id=?", "kind=?"]
        params: list[object] = [tenant_id, kind]
        if not include_deleted:
            clauses.append("deleted_at IS NULL")
        rows = self.connection.execute(
            "SELECT tenant_id, kind, record_id, revision, payload_json, created_at, updated_at, "
            "created_by_user_id, deleted_at FROM enterprise_records WHERE "
            + " AND ".join(clauses)
            + " ORDER BY created_at DESC, record_id ASC LIMIT ?",
            (*params, max(1, min(limit, 500))),
        ).fetchall()
        items = [self._row(row) for row in rows]
        if status:
            items = [item for item in items if str(item.get("status", "")) == status]
        if project_id:
            items = [item for item in items if str(item.get("project_id", "")) == project_id]
        if search:
            needle = search.casefold()
            items = [
                item
                for item in items
                if needle in json.dumps(item, ensure_ascii=False, sort_keys=True).casefold()
            ]
        return tuple(items)

    def create(
        self,
        tenant_id: str,
        kind: str,
        payload: Mapping[str, object],
        *,
        actor_id: str,
        idempotency_key: str | None,
    ) -> dict[str, object]:
        fingerprint = self._fingerprint(payload, kind)
        if idempotency_key:
            existing = self.connection.execute(
                "SELECT record_id, fingerprint FROM enterprise_idempotency "
                "WHERE tenant_id=? AND operation=? AND idempotency_key=?",
                (tenant_id, kind, idempotency_key),
            ).fetchone()
            if existing is not None:
                if str(existing[1]) != fingerprint:
                    raise EnterpriseApiError(409, "IDEMPOTENCY_KEY_REUSE")
                return self.get(tenant_id, kind, str(existing[0]))
        record_id = f"{_ID_PREFIX[kind]}-{uuid4().hex}"
        now = _iso(_now())
        stored = {**payload, "status": payload.get("status", "active")}
        self.connection.execute(
            "INSERT INTO enterprise_records "
            "(tenant_id, kind, record_id, revision, payload_json, created_at, updated_at, created_by_user_id) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (tenant_id, kind, record_id, 1, json.dumps(stored, sort_keys=True, ensure_ascii=False), now, None, actor_id),
        )
        if idempotency_key:
            self.connection.execute(
                "INSERT INTO enterprise_idempotency (tenant_id, operation, idempotency_key, record_id, fingerprint) "
                "VALUES (?,?,?,?,?)",
                (tenant_id, kind, idempotency_key, record_id, fingerprint),
            )
        self._audit(tenant_id, actor_id, "create", kind, record_id, detail={"revision": 1})
        self.connection.commit()
        return self.get(tenant_id, kind, record_id)

    def update(
        self,
        tenant_id: str,
        kind: str,
        record_id: str,
        payload: Mapping[str, object],
        *,
        actor_id: str,
        expected_revision: int,
    ) -> dict[str, object]:
        current = self.get(tenant_id, kind, record_id, include_deleted=True)
        if int(current["revision"]) != expected_revision:
            raise EnterpriseApiError(409, "REVISION_CONFLICT")
        immutable = set(payload) & _IMMUTABLE_FIELDS
        if immutable:
            raise EnterpriseApiError(400, "IMMUTABLE_FIELDS")
        merged = {
            key: value
            for key, value in current.items()
            if key not in {"tenant_id", "kind", "record_id", "revision", "created_at", "updated_at", "created_by_user_id", "deleted_at"}
        }
        merged.update(payload)
        merged["status"] = payload.get("status", str(current.get("status", "active")))
        now = _iso(_now())
        self.connection.execute(
            "UPDATE enterprise_records SET revision=?, payload_json=?, updated_at=? "
            "WHERE tenant_id=? AND kind=? AND record_id=? AND revision=?",
            (
                expected_revision + 1,
                json.dumps(merged, sort_keys=True, ensure_ascii=False),
                now,
                tenant_id,
                kind,
                record_id,
                expected_revision,
            ),
        )
        self._audit(tenant_id, actor_id, "update", kind, record_id, detail={"revision": expected_revision + 1})
        self.connection.commit()
        return self.get(tenant_id, kind, record_id, include_deleted=True)

    def delete(
        self, tenant_id: str, kind: str, record_id: str, *, actor_id: str, expected_revision: int
    ) -> dict[str, object]:
        current = self.get(tenant_id, kind, record_id)
        if int(current["revision"]) != expected_revision:
            raise EnterpriseApiError(409, "REVISION_CONFLICT")
        now = _iso(_now())
        self.connection.execute(
            "UPDATE enterprise_records SET revision=?, deleted_at=?, updated_at=? "
            "WHERE tenant_id=? AND kind=? AND record_id=? AND revision=?",
            (expected_revision + 1, now, now, tenant_id, kind, record_id, expected_revision),
        )
        self._audit(tenant_id, actor_id, "delete", kind, record_id, detail={"revision": expected_revision + 1})
        self.connection.commit()
        return self.get(tenant_id, kind, record_id, include_deleted=True)

    def restore(
        self, tenant_id: str, kind: str, record_id: str, *, actor_id: str, expected_revision: int
    ) -> dict[str, object]:
        current = self.get(tenant_id, kind, record_id, include_deleted=True)
        if current["deleted_at"] is None:
            raise EnterpriseApiError(409, "RECORD_NOT_DELETED")
        if int(current["revision"]) != expected_revision:
            raise EnterpriseApiError(409, "REVISION_CONFLICT")
        now = _iso(_now())
        self.connection.execute(
            "UPDATE enterprise_records SET revision=?, deleted_at=NULL, updated_at=? "
            "WHERE tenant_id=? AND kind=? AND record_id=? AND revision=?",
            (expected_revision + 1, now, tenant_id, kind, record_id, expected_revision),
        )
        self._audit(tenant_id, actor_id, "restore", kind, record_id, detail={"revision": expected_revision + 1})
        self.connection.commit()
        return self.get(tenant_id, kind, record_id)

    def audit(self, tenant_id: str, limit: int = 200) -> tuple[dict[str, object], ...]:
        rows = self.connection.execute(
            "SELECT event_id, actor_id, action, target_kind, target_id, decision, occurred_at, detail_json "
            "FROM enterprise_audit WHERE tenant_id=? ORDER BY occurred_at DESC LIMIT ?",
            (tenant_id, max(1, min(limit, 500))),
        ).fetchall()
        return tuple(
            {
                "event_id": row[0],
                "actor_id": row[1],
                "action": row[2],
                "target_kind": row[3],
                "target_id": row[4],
                "decision": row[5],
                "occurred_at": row[6],
                "detail": json.loads(row[7]),
            }
            for row in rows
        )

    def record_decision(
        self,
        tenant_id: str,
        approval_id: str,
        payload: Mapping[str, object],
        *,
        actor_id: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        approval = self.get(tenant_id, "approvals", approval_id)
        expected = payload.get("expected_revision")
        if isinstance(expected, bool) or not isinstance(expected, int):
            raise EnterpriseApiError(400, "EXPECTED_REVISION_REQUIRED")
        decision = str(payload.get("decision", "")).strip()
        if decision not in {"approve", "reject", "request_changes"}:
            raise EnterpriseApiError(400, "DECISION_INVALID")
        fingerprint = hashlib.sha256(
            json.dumps(
                {"approval_id": approval_id, "expected": expected, "decision": decision, "comment": payload.get("comment")},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        existing = self.connection.execute(
            "SELECT record_id, fingerprint FROM enterprise_idempotency "
            "WHERE tenant_id=? AND operation=? AND idempotency_key=?",
            (tenant_id, f"approval-decision:{approval_id}", idempotency_key),
        ).fetchone()
        if existing is not None:
            # A decision is a one-shot act. Replaying the key is rejected even
            # when the payload matches, so an approval cannot be recorded twice.
            raise EnterpriseApiError(409, "DUPLICATE_DECISION")
        if int(approval["revision"]) != expected:
            raise EnterpriseApiError(409, "STALE_REVISION")
        decision_id = f"dsc-{uuid4().hex}"
        now = _iso(_now())
        self.connection.execute(
            "INSERT INTO enterprise_approval_decisions "
            "(tenant_id, approval_id, decision_id, expected_revision, decision, comment, actor_id, occurred_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (tenant_id, approval_id, decision_id, expected, decision, payload.get("comment"), actor_id, now),
        )
        self.connection.execute(
            "INSERT INTO enterprise_idempotency (tenant_id, operation, idempotency_key, record_id, fingerprint) "
            "VALUES (?,?,?,?,?)",
            (tenant_id, f"approval-decision:{approval_id}", idempotency_key, decision_id, fingerprint),
        )
        next_status = {"approve": "approved", "reject": "rejected", "request_changes": "changes_requested"}[decision]
        merged = {
            key: value
            for key, value in approval.items()
            if key not in {"tenant_id", "kind", "record_id", "revision", "created_at", "updated_at", "created_by_user_id", "deleted_at"}
        }
        merged["status"] = next_status
        self.connection.execute(
            "UPDATE enterprise_records SET revision=?, payload_json=?, updated_at=? "
            "WHERE tenant_id=? AND kind=? AND record_id=? AND revision=?",
            (
                expected + 1,
                json.dumps(merged, sort_keys=True, ensure_ascii=False),
                now,
                tenant_id,
                "approvals",
                approval_id,
                expected,
            ),
        )
        self._audit(tenant_id, actor_id, "decision", "approvals", approval_id, detail={"decision": decision, "revision": expected + 1})
        self.connection.commit()
        return self._decision(tenant_id, approval_id, decision_id)

    def _decision(self, tenant_id: str, approval_id: str, decision_id: str) -> dict[str, object]:
        row = self.connection.execute(
            "SELECT decision_id, expected_revision, decision, comment, actor_id, occurred_at "
            "FROM enterprise_approval_decisions WHERE tenant_id=? AND approval_id=? AND decision_id=?",
            (tenant_id, approval_id, decision_id),
        ).fetchone()
        if row is None:
            raise EnterpriseApiError(404, "DECISION_NOT_FOUND")
        return {
            "decision_id": row[0],
            "approval_id": approval_id,
            "expected_revision": int(row[1]),
            "decision": row[2],
            "comment": row[3],
            "actor_id": row[4],
            "occurred_at": row[5],
        }

    def decisions(self, tenant_id: str, approval_id: str) -> tuple[dict[str, object], ...]:
        rows = self.connection.execute(
            "SELECT decision_id FROM enterprise_approval_decisions WHERE tenant_id=? AND approval_id=? "
            "ORDER BY occurred_at DESC",
            (tenant_id, approval_id),
        ).fetchall()
        return tuple(self._decision(tenant_id, approval_id, str(row[0])) for row in rows)

    def publish_workflow(
        self, tenant_id: str, workflow_id: str, payload: Mapping[str, object], *, actor_id: str, expected_revision: int
    ) -> dict[str, object]:
        current = self.get(tenant_id, "workflows", workflow_id)
        if int(current["revision"]) != expected_revision:
            raise EnterpriseApiError(409, "REVISION_CONFLICT")
        steps = payload.get("steps", current.get("steps"))
        transitions = payload.get("transitions", current.get("transitions", []))
        errors = _validate_workflow(steps, transitions)
        if errors:
            raise EnterpriseApiError(400, "WORKFLOW_INVALID:" + ";".join(errors))
        version = int(current.get("published_version", 0)) + 1
        merged = {
            key: value
            for key, value in current.items()
            if key not in {"tenant_id", "kind", "record_id", "revision", "created_at", "updated_at", "created_by_user_id", "deleted_at"}
        }
        merged.update({"steps": steps, "transitions": transitions, "status": "published", "published_version": version})
        now = _iso(_now())
        self.connection.execute(
            "UPDATE enterprise_records SET revision=?, payload_json=?, updated_at=? "
            "WHERE tenant_id=? AND kind=? AND record_id=? AND revision=?",
            (
                expected_revision + 1,
                json.dumps(merged, sort_keys=True, ensure_ascii=False),
                now,
                tenant_id,
                "workflows",
                workflow_id,
                expected_revision,
            ),
        )
        self._audit(tenant_id, actor_id, "publish", "workflows", workflow_id, detail={"version": version, "revision": expected_revision + 1})
        self.connection.commit()
        return self.get(tenant_id, "workflows", workflow_id)


def _validate_workflow(steps: object, transitions: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(steps, list) or len(steps) < 2:
        return ["at least two steps are required"]
    if not isinstance(transitions, list):
        return ["transitions must be a list"]
    ids: list[str] = []
    for step in steps:
        if not isinstance(step, dict) or not str(step.get("id", "")).strip() or not str(step.get("name", "")).strip():
            errors.append("every step needs an id and name")
            continue
        ids.append(str(step["id"]))
    if len(set(ids)) != len(ids):
        errors.append("step ids must be unique")
    if not any(isinstance(step, dict) and step.get("terminal") for step in steps):
        errors.append("at least one terminal step is required")
    seen: set[tuple[str, str]] = set()
    for transition in transitions:
        if not isinstance(transition, dict):
            errors.append("transition must be an object")
            continue
        source, target = str(transition.get("from", "")), str(transition.get("to", ""))
        if source not in ids or target not in ids:
            errors.append("transition references a missing step")
        if source == target:
            errors.append("a step cannot transition to itself")
        if (source, target) in seen:
            errors.append("duplicate transition")
        seen.add((source, target))
    if ids:
        reachable = {ids[0]}
        changed = True
        while changed:
            changed = False
            for transition in transitions:
                if not isinstance(transition, dict):
                    continue
                if transition.get("from") in reachable and transition.get("to") not in reachable:
                    reachable.add(transition.get("to"))
                    changed = True
        for step in steps:
            if isinstance(step, dict) and step.get("id") not in reachable:
                errors.append(f"step {step.get('id')} is unreachable")
    return list(dict.fromkeys(errors))


class EnterpriseWorkbenchHttpMiddleware:
    """Authenticated /api/enterprise/* surface for the preview runtime."""

    def __init__(self, app: Callable, lifecycle_api: object, store: EnterpriseWorkbenchStore) -> None:
        self._app = app
        self._lifecycle = lifecycle_api
        self._store = store

    def __call__(self, environ: Mapping[str, object], start_response: Callable):
        path = str(environ.get("PATH_INFO", "/") or "/")
        if not self._owns(path):
            return self._app(environ, start_response)
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        try:
            status, payload = self._handle(method, path, environ)
        except EnterpriseApiError as exc:
            status, payload = exc.status, {"code": exc.code}
        except SessionError:
            status, payload = 401, {"code": "SESSION_REQUIRED"}
        except (ProjectLifecycleError, PermissionError):
            status, payload = 403, {"code": "ENTERPRISE_ACCESS_DENIED"}
        except Exception:
            traceback.print_exc()
            status, payload = 500, {"code": "ENTERPRISE_INTERNAL_ERROR"}
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        reason = {
            200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized",
            403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 409: "Conflict",
            500: "Internal Server Error", 503: "Service Unavailable",
        }.get(status, "OK")
        start_response(
            f"{status} {reason}",
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )
        return [body]

    @staticmethod
    def _owns(path: str) -> bool:
        if not path.startswith("/api/enterprise/"):
            return False
        # The mature Task API middleware owns its own routes.
        return not (path == "/api/enterprise/tasks" or path.startswith("/api/enterprise/tasks/"))

    def _handle(self, method: str, path: str, environ: Mapping[str, object]):
        session = self._session(environ)
        role_set = frozenset(getattr(session, "roles", ()))
        parts = [unquote(part) for part in path.strip("/").split("/")]
        # parts = ["api","enterprise", kind, id?, action?]
        if len(parts) < 3:
            raise EnterpriseApiError(404, "ROUTE_NOT_FOUND")
        kind = parts[2]
        if kind in {"portlets", "portfolio", "evm"}:
            return 503, {"code": "ENGINEERING_SOURCE_NOT_CONNECTED"}
        if kind == "audit":
            if method != "GET":
                raise EnterpriseApiError(405, "METHOD_NOT_ALLOWED")
            self._require_read(role_set)
            return 200, {"contract_version": "cubi-enterprise-audit.v1", "items": list(self._store.audit(session.tenant_id))}
        if kind not in _KINDS:
            raise EnterpriseApiError(404, "ROUTE_NOT_FOUND")
        if len(parts) == 3:
            if method == "GET":
                self._require_read(role_set)
                query = parse_qs(str(environ.get("QUERY_STRING", "") or ""), keep_blank_values=False)
                items = self._store.list(
                    session.tenant_id,
                    kind,
                    status=_one(query, "status"),
                    project_id=_one(query, "project_id"),
                    search=_one(query, "q"),
                    limit=int(_one(query, "limit") or 100),
                )
                return 200, {"contract_version": f"cubi-enterprise-{kind}.v1", "items": list(items), "next_cursor": None}
            if method == "POST":
                self._require_write(role_set, kind)
                payload = self._body(environ)
                self._validate_payload(kind, payload)
                record = self._store.create(
                    session.tenant_id,
                    kind,
                    payload,
                    actor_id=session.user_id,
                    idempotency_key=_header(environ, "Idempotency-Key"),
                )
                return 201, {"record": record}
            raise EnterpriseApiError(405, "METHOD_NOT_ALLOWED")
        record_id = parts[3]
        if len(parts) == 5:
            action = parts[4]
            if kind == "approvals" and action == "decisions":
                if method == "GET":
                    self._require_read(role_set)
                    return 200, {"contract_version": "cubi-enterprise-approval-decisions.v1", "items": list(self._store.decisions(session.tenant_id, record_id))}
                if method == "POST":
                    self._require_write(role_set, kind)
                    key = _header(environ, "Idempotency-Key")
                    if not key:
                        raise EnterpriseApiError(400, "IDEMPOTENCY_KEY_REQUIRED")
                    decision = self._store.record_decision(
                        session.tenant_id, record_id, self._body(environ), actor_id=session.user_id, idempotency_key=key
                    )
                    return 201, {"decision": decision}
                raise EnterpriseApiError(405, "METHOD_NOT_ALLOWED")
            if kind == "workflows" and action == "publish":
                if method != "POST":
                    raise EnterpriseApiError(405, "METHOD_NOT_ALLOWED")
                self._require_write(role_set, kind)
                payload = self._body(environ)
                expected = payload.get("expected_revision")
                if isinstance(expected, bool) or not isinstance(expected, int):
                    raise EnterpriseApiError(400, "EXPECTED_REVISION_REQUIRED")
                record = self._store.publish_workflow(
                    session.tenant_id, record_id, payload, actor_id=session.user_id, expected_revision=expected
                )
                return 200, {"record": record}
            if action == "restore":
                if method != "POST":
                    raise EnterpriseApiError(405, "METHOD_NOT_ALLOWED")
                self._require_write(role_set, kind)
                expected = self._body(environ).get("expected_revision")
                if isinstance(expected, bool) or not isinstance(expected, int):
                    raise EnterpriseApiError(400, "EXPECTED_REVISION_REQUIRED")
                record = self._store.restore(
                    session.tenant_id, kind, record_id, actor_id=session.user_id, expected_revision=expected
                )
                return 200, {"record": record}
            raise EnterpriseApiError(404, "ROUTE_NOT_FOUND")
        if len(parts) == 4:
            if method == "GET":
                self._require_read(role_set)
                return 200, {"record": self._store.get(session.tenant_id, kind, record_id)}
            if method == "PATCH":
                self._require_write(role_set, kind)
                payload = self._body(environ)
                expected = payload.pop("expected_revision", None)
                if isinstance(expected, bool) or not isinstance(expected, int):
                    raise EnterpriseApiError(400, "EXPECTED_REVISION_REQUIRED")
                record = self._store.update(
                    session.tenant_id, kind, record_id, payload, actor_id=session.user_id, expected_revision=expected
                )
                return 200, {"record": record}
            if method == "DELETE":
                self._require_write(role_set, kind)
                expected = self._body_or_empty(environ).get("expected_revision")
                if isinstance(expected, bool) or not isinstance(expected, int):
                    raise EnterpriseApiError(400, "EXPECTED_REVISION_REQUIRED")
                record = self._store.delete(
                    session.tenant_id, kind, record_id, actor_id=session.user_id, expected_revision=expected
                )
                return 200, {"record": record}
            raise EnterpriseApiError(405, "METHOD_NOT_ALLOWED")
        raise EnterpriseApiError(404, "ROUTE_NOT_FOUND")

    def _session(self, environ: Mapping[str, object]):
        from http.cookies import SimpleCookie

        cookie = SimpleCookie()
        try:
            cookie.load(str(environ.get("HTTP_COOKIE", "") or ""))
        except Exception:
            cookie = SimpleCookie()
        morsel = cookie.get("cp_session")
        if morsel is None or not morsel.value:
            raise EnterpriseApiError(401, "SESSION_REQUIRED")
        try:
            session = self._lifecycle.get_session(morsel.value, now=_now())
        except (ProjectLifecycleError, SessionError) as exc:
            raise EnterpriseApiError(401, "SESSION_REQUIRED") from exc
        if session is None or not getattr(session, "tenant_id", None) or not getattr(session, "user_id", None):
            raise EnterpriseApiError(401, "SESSION_REQUIRED")
        return session

    @staticmethod
    def _require_read(roles: frozenset[str]) -> None:
        if not roles & ENTERPRISE_READ_ROLES:
            raise EnterpriseApiError(403, "ENTERPRISE_ACCESS_DENIED")

    @staticmethod
    def _require_write(roles: frozenset[str], kind: str) -> None:
        if kind in _ADMIN_KINDS and not roles & ENTERPRISE_ADMIN_ROLES:
            raise EnterpriseApiError(403, "ENTERPRISE_ADMIN_REQUIRED")
        if not roles & ENTERPRISE_WRITE_ROLES:
            raise EnterpriseApiError(403, "ENTERPRISE_WRITE_DENIED")

    @staticmethod
    def _validate_payload(kind: str, payload: Mapping[str, object]) -> None:
        tenant = payload.get("tenant_id")
        if tenant is not None:
            # Tenant is always derived from the session; the client may not
            # choose or override it.
            raise EnterpriseApiError(403, "TENANT_IS_CLIENT_CONTROLLED")
        for field in _REQUIRED_FIELDS.get(kind, ()):
            value = payload.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise EnterpriseApiError(400, f"{field.upper()}_REQUIRED")
        if kind == "memberships" and str(payload.get("role")) not in {
            "owner", "admin", "project_manager", "approver", "field_worker", "member", "viewer",
        }:
            raise EnterpriseApiError(400, "MEMBERSHIP_ROLE_INVALID")
        email = payload.get("email")
        if email is not None and (not isinstance(email, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)):
            raise EnterpriseApiError(400, "EMAIL_INVALID")

    @staticmethod
    def _body(environ: Mapping[str, object]) -> dict[str, object]:
        import json as _json

        raw = _body_bytes(environ)
        if not raw:
            return {}
        try:
            payload = _json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, _json.JSONDecodeError) as exc:
            raise EnterpriseApiError(400, "INVALID_JSON") from exc
        if not isinstance(payload, dict):
            raise EnterpriseApiError(400, "INVALID_JSON")
        return payload

    @staticmethod
    def _body_or_empty(environ: Mapping[str, object]) -> dict[str, object]:
        try:
            return EnterpriseWorkbenchHttpMiddleware._body(environ)
        except EnterpriseApiError:
            return {}


def _body_bytes(environ: Mapping[str, object]) -> bytes:
    try:
        length = int(str(environ.get("CONTENT_LENGTH", "") or "0"))
    except ValueError:
        return b""
    if length <= 0 or length > 1_048_576:
        return b""
    stream = environ.get("wsgi.input")
    raw = stream.read(length) if hasattr(stream, "read") else b""
    return raw or b""


def _header(environ: Mapping[str, object], name: str) -> str | None:
    key = "HTTP_" + name.upper().replace("-", "_")
    value = str(environ.get(key, "") or "").strip()
    return value or None


def _one(query: Mapping[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    if len(values) != 1:
        return None
    value = values[0].strip()
    return value or None
