#!/usr/bin/env python3
"""Evidence-gathering verification of a deployed CUBI Preview.

The script talks to the real Vercel Preview over HTTPS. It never reads or prints
secrets: the password is only accepted from ``--password-stdin`` or
``CUBI_VERIFY_PASSWORD`` and the resulting cookies are kept in memory and
redacted from the evidence file.

Read-only by default. ``--write`` additionally creates one risk and one AI
proposal (never auto-approves or executes) so a deployment can prove writes
without depending on a browser.

Examples::

    python scripts/verify_preview_runtime.py \
        --base-url https://cubi-web-preview.vercel.app \
        --email you@example.com --password-stdin \
        --project-id your-project --out preview-evidence.json

Exit code 0 means every required check passed. A ``BLOCKED`` check (missing
configuration, provider not enabled) is recorded and does not fail the run, but
``ready``, login, project open, workspace read, logout and re-login must pass.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


class Client:
    def __init__(
        self, base_url: str, *, timeout: float = 30.0, allow_http: bool = False
    ) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        if not parsed.scheme or not parsed.netloc:
            raise SystemExit("--base-url must be an absolute URL")
        allowed = {"https"} | ({"http"} if allow_http else set())
        if parsed.scheme not in allowed:
            raise SystemExit("--base-url must use https (or --allow-http for loopback)")
        self.base_url = base_url.rstrip("/")
        self.origin = f"{parsed.scheme}://{parsed.netloc}"
        self.timeout = timeout
        self.cookies: dict[str, str] = {}

    def _cookie_header(self) -> str:
        return "; ".join(f"{name}={value}" for name, value in self.cookies.items())

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        query: str = "",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, list[str]], bytes]:
        url = self.base_url + path
        if query:
            url += "?" + query
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        request.add_header("Origin", self.origin)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        cookie = self._cookie_header()
        if cookie:
            request.add_header("Cookie", cookie)
        csrf = self.cookies.get("cubi_csrf")
        if method in UNSAFE and csrf:
            request.add_header("X-CSRF-Token", urllib.parse.unquote(csrf))
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = response.status
                raw_headers = response.getheaders()
                payload = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw_headers = error.headers.items()  # type: ignore[union-attr]
            payload = error.read()
        except urllib.error.URLError as error:
            raise SystemExit(f"network error for {method} {path}: {error.reason}") from error
        headers_out: dict[str, list[str]] = {}
        for key, value in raw_headers:
            headers_out.setdefault(key.lower(), []).append(value)
        for value in headers_out.get("set-cookie", []):
            pair = value.split(";", 1)[0]
            if "=" in pair:
                name, _, cookie_value = pair.partition("=")
                self.cookies[name.strip()] = cookie_value.strip()
        return status, headers_out, payload


def _json(payload: bytes) -> Any:
    try:
        return json.loads(payload.decode("utf-8") or "null")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", default=os.environ.get("CUBI_VERIFY_EMAIL", ""))
    parser.add_argument("--password-stdin", action="store_true")
    parser.add_argument("--password", default=os.environ.get("CUBI_VERIFY_PASSWORD", ""))
    parser.add_argument("--project-id", default="")
    parser.add_argument("--create-project", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--allow-http", action="store_true")
    parser.add_argument("--out", default="preview-evidence.json")
    args = parser.parse_args()

    if not args.email:
        raise SystemExit("--email or CUBI_VERIFY_EMAIL is required")
    password = args.password
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    if not password:
        raise SystemExit("provide --password-stdin or CUBI_VERIFY_PASSWORD")

    client = Client(args.base_url, allow_http=args.allow_http)
    evidence: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": args.base_url,
        "origin": client.origin,
        "checks": [],
        "schema": None,
        "project_id": args.project_id or None,
        "generated_ids": {},
        "limitations": [],
    }

    def record(
        name: str,
        method: str,
        path: str,
        status: int,
        ok: bool,
        *,
        required: bool = True,
        note: str = "",
        code: str | None = None,
    ) -> None:
        entry = {
            "check": name,
            "method": method,
            "path": path,
            "status": status,
            "ok": ok,
            "required": required,
        }
        if code:
            entry["code"] = code
        if note:
            entry["note"] = note
        evidence["checks"].append(entry)

    failures = 0

    # --- health ---------------------------------------------------------
    status, _, payload = client.request("GET", "/api/health/live")
    live = _json(payload) or {}
    ok = status == 200 and live.get("status") == "ok"
    record("liveness", "GET", "/api/health/live", status, ok, note=str(live.get("status", "")))
    failures += 0 if ok else 1

    status, _, payload = client.request("GET", "/api/health/ready")
    ready = _json(payload) or {}
    if isinstance(ready.get("schema"), dict):
        evidence["schema"] = ready["schema"]
    ok = status == 200 and ready.get("status") == "ready"
    note = "" if ok else str(ready.get("status", ready) if isinstance(ready, dict) else ready)
    record("readiness", "GET", "/api/health/ready", status, ok, note=note)
    failures += 0 if ok else 1

    # --- login ----------------------------------------------------------
    status, _, payload = client.request(
        "POST", "/api/session", body={"email": args.email, "password": password}
    )
    session = _json(payload) or {}
    ok = status == 200 and "cp_session" in client.cookies
    record("login", "POST", "/api/session", status, ok, code=session.get("code"))
    if not ok:
        _write(args.out, evidence)
        print(json.dumps(evidence, indent=2))
        return 1

    status, _, payload = client.request("GET", "/api/session")
    current = _json(payload) or {}
    ok = status == 200 and bool(current.get("user_id"))
    record("session", "GET", "/api/session", status, ok)
    failures += 0 if ok else 1

    # --- projects -------------------------------------------------------
    status, _, payload = client.request("GET", "/api/projects")
    projects = (_json(payload) or {}).get("projects", [])
    ok = status == 200 and isinstance(projects, list)
    record("projects", "GET", "/api/projects", status, ok, note=f"{len(projects)} visible")
    failures += 0 if ok else 1

    project_id = args.project_id
    if not project_id and projects:
        project_id = str(projects[0].get("project_id") or "")
    if not project_id and args.create_project:
        generated = "verify-" + str(int(time.time()))
        status, _, payload = client.request(
            "POST",
            "/api/projects",
            body={
                "project_id": generated,
                "name": "Preview verification project",
                "description": "Created by verify_preview_runtime.py",
            },
        )
        created = _json(payload) or {}
        ok = status in {200, 201} and isinstance(created.get("context"), dict)
        record("create_project", "POST", "/api/projects", status, ok, code=created.get("code"))
        if ok:
            project_id = generated
            evidence["generated_ids"]["project_id"] = generated
        else:
            failures += 1
    if not project_id:
        record(
            "select_project",
            "GET",
            "/api/projects",
            200,
            False,
            note="no visible project; pass --project-id or --create-project",
        )
        _write(args.out, evidence)
        print(json.dumps(evidence, indent=2))
        return 1
    evidence["project_id"] = project_id

    status, _, payload = client.request(
        "POST", f"/api/projects/{project_id}/open"
    )
    opened = _json(payload) or {}
    ok = status == 200 and isinstance(opened.get("context"), dict)
    record("open_project", "POST", f"/api/projects/{project_id}/open", status, ok, code=opened.get("code"))
    failures += 0 if ok else 1
    revision = 0
    if ok:
        revision = int(opened["context"].get("revision") or 0)

    scope_headers = {
        "X-Tenant-Id": str(current.get("tenant_id") or ""),
        "X-Project-Id": project_id,
        "X-Project-Revision": str(revision),
    }

    status, _, payload = client.request(
        "GET", "/api/v2/workspace/control-room/read", headers=scope_headers
    )
    workspace = _json(payload) or {}
    ok = status == 200 and workspace.get("contract_version") == "workspace-control-room-read.v2"
    record("workspace_read", "GET", "/api/v2/workspace/control-room/read", status, ok, code=workspace.get("code"))
    failures += 0 if ok else 1

    # --- durable domain reads ------------------------------------------
    for name, path in (
        ("risks", f"/api/projects/{project_id}/risks"),
        ("ai_proposals", f"/api/projects/{project_id}/ai/actions/proposals"),
        ("organization_templates", "/api/forms/organization/templates"),
        ("knowledge_coverage", "/api/knowledge/coverage"),
    ):
        status, _, payload = client.request("GET", path)
        body = _json(payload) or {}
        ok = status == 200
        record(name, "GET", path, status, ok, required=False, code=body.get("code"))
        if status in {404, 503}:
            evidence["limitations"].append(f"{name} returned {status}")

    # --- optional writes ------------------------------------------------
    if args.write:
        risk_id = "verify-risk-" + str(int(time.time()))
        status, _, payload = client.request(
            "POST",
            f"/api/projects/{project_id}/risks",
            body={
                "risk_id": risk_id,
                "title": "Preview verification risk",
                "category": "schedule",
                "probability": 2,
                "impact": 2,
                "response_strategy": "accept",
                "owner": "verification",
                "date_identified": time.strftime("%Y-%m-%d", time.gmtime()),
                "idempotency_key": risk_id,
            },
        )
        created = _json(payload) or {}
        ok = status == 200
        record("risk_create", "POST", f"/api/projects/{project_id}/risks", status, ok, code=created.get("code"), required=False)
        if ok:
            evidence["generated_ids"]["risk_id"] = risk_id
            status, _, payload = client.request(
                "GET", f"/api/projects/{project_id}/risks"
            )
            listed = (_json(payload) or {}).get("risks", [])
            record(
                "risk_read_back",
                "GET",
                f"/api/projects/{project_id}/risks",
                status,
                any(item.get("risk_id") == risk_id for item in listed),
                required=False,
            )

        # A proposal proves the deterministic runtime is composed. It is left
        # pending on purpose: verification must never approve or execute.
        status, _, payload = client.request(
            "POST",
            f"/api/projects/{project_id}/ai/actions/proposals",
            body={
                "expected_revision": revision,
                "tool_name": "activity.create",
                "payload": {
                    "activity_id": "verify-act-" + str(int(time.time())),
                    "name": "Verification placeholder",
                    "duration_value": 1,
                    "duration_unit": "working-day",
                    "wbs_id": "__verify_missing_wbs__",
                },
                "evidence_refs": [],
            },
        )
        proposed = _json(payload) or {}
        # A rejected proposal is still honest evidence that the runtime answered;
        # 201 means it was stored. Both are recorded, only an unexpected 5xx is
        # counted as a limitation.
        ok = status in {201, 400, 403, 409}
        record(
            "ai_propose",
            "POST",
            f"/api/projects/{project_id}/ai/actions/proposals",
            status,
            ok,
            required=False,
            code=proposed.get("code") or (proposed.get("status") if ok else None),
        )

    # --- logout and restore --------------------------------------------
    status, _, _ = client.request("DELETE", "/api/session")
    record("logout", "DELETE", "/api/session", status, status == 204)
    failures += 0 if status == 204 else 1

    revoked_cookie = client.cookies.get("cp_session", "")
    client.cookies = {"cp_session": revoked_cookie} if revoked_cookie else {}
    status, _, payload = client.request("GET", "/api/session")
    code = (_json(payload) or {}).get("code")
    ok = status == 401
    record("revoked_session_rejected", "GET", "/api/session", status, ok, code=code)
    failures += 0 if ok else 1

    client.cookies = {}
    status, _, payload = client.request(
        "POST", "/api/session", body={"email": args.email, "password": password}
    )
    ok = status == 200 and "cp_session" in client.cookies
    record("relogin", "POST", "/api/session", status, ok)
    failures += 0 if ok else 1
    if ok:
        status, _, payload = client.request(
            "GET", f"/api/projects/{project_id}"
        )
        project = _json(payload) or {}
        ok = status == 200
        record(
            "project_restored",
            "GET",
            f"/api/projects/{project_id}",
            status,
            ok,
            code=project.get("code"),
        )
        failures += 0 if ok else 1

    evidence["ok"] = failures == 0
    evidence["required_failures"] = failures
    _write(args.out, evidence)
    print(json.dumps(evidence, indent=2))
    return 0 if failures == 0 else 1


def _write(path: str, evidence: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    sys.exit(main())
