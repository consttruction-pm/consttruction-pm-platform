from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_layout_definition_repository import PersistedP6Layout
from construction_pm.preview.runtime import PreviewRepositories, open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}/backup"


def _request(
    app,
    method: str,
    path: str,
    *,
    body: dict | None = None,
    cookie: str | None = None,
):
    raw = b"" if body is None else json.dumps(body).encode()
    path_only, _, query_string = path.partition("?")
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path_only,
        "QUERY_STRING": query_string,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    if raw:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _json(body: bytes) -> dict:
    return json.loads(body)


def _scope(runtime) -> BackendScope:
    context = runtime.lifecycle_api.open_project(
        runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"]).session_id,
        PROJECT,
        now=datetime.now(timezone.utc),
    ).context
    return BackendScope(context.tenant_id, context.project_id, context.revision)


def test_project_snapshot_content_is_checksummed_and_listed(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        scope = _scope(runtime)
        status, body = _request(
            runtime.app,
            "POST",
            BASE,
            body={
                "kind": "project",
                "label": "Nightly project backup",
                "idempotency_key": "backup-create-1",
            },
            cookie=admin.session_id,
        )
        assert status == 201, body[:500]
        created = _json(body)
        assert created["contract_version"] == "p6-backup-api.v1"
        assert created["snapshot_id"] == "BKP-1"
        assert created["kind"] == "project"
        assert created["replayed"] is False
        assert set(created["section_counts"]) == {
            "wbs",
            "activities",
            "resources",
            "relationships",
        }
        assert all(count > 0 for count in created["section_counts"].values())
        assert len(created["content_sha256"]) == 64

        status, body = _request(
            runtime.app, "GET", BASE, cookie=admin.session_id
        )
        assert status == 200, body[:400]
        listed = _json(body)["snapshots"]
        assert [item["snapshot_id"] for item in listed] == ["BKP-1"]
        assert listed[0]["label"] == "Nightly project backup"

        status, body = _request(
            runtime.app, "GET", f"{BASE}/BKP-1", cookie=admin.session_id
        )
        assert status == 200, body[:400]
        detail = _json(body)
        assert detail["project_revision"] == created["project_revision"]
        assert detail["content_sha256"] == created["content_sha256"]

        status, body = _request(
            runtime.app, "GET", f"{BASE}/BKP-1/content", cookie=admin.session_id
        )
        assert status == 200, body[:400]
        content = _json(body)
        assert content["snapshot_id"] == "BKP-1"
        assert (
            sorted(content["sections"]) == sorted(created["section_counts"])
        )
        for name, records in content["sections"].items():
            assert len(records) == created["section_counts"][name]
        digest = hashlib.sha256(
            json.dumps(
                {
                    "format": "cubi-backup.v1",
                    "kind": "project",
                    "project_revision": content["project_revision"],
                    "sections": content["sections"],
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        assert digest == content["content_sha256"]

        runtime.connection.execute(
            "UPDATE project_backup_snapshot SET content_json=? WHERE tenant_id=? AND project_id=? AND snapshot_id=?",
            (
                "{\"format\":\"cubi-backup.v1\",\"kind\":\"project\",\"project_revision\":7,\"sections\":{}}",
                scope.tenant_id,
                PROJECT,
                "BKP-1",
            ),
        )
        runtime.connection.commit()
        status, body = _request(
            runtime.app, "GET", f"{BASE}/BKP-1/content", cookie=admin.session_id
        )
        assert status == 400, body[:400]
        assert _json(body)["code"] == "BACKUP_INTEGRITY_FAILED"
    finally:
        runtime.close()


def test_layouts_snapshot_restores_the_captured_layout(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        scope = _scope(runtime)
        repositories = PreviewRepositories.create(runtime.connection)
        head = repositories.layouts.get(scope, "project", "activity")
        assert head is not None
        original_metadata = dict(head.metadata)

        status, body = _request(
            runtime.app,
            "POST",
            BASE,
            body={
                "kind": "layouts",
                "label": "Layout baseline",
                "idempotency_key": "layout-backup-1",
            },
            cookie=admin.session_id,
        )
        assert status == 201, body[:500]
        snapshot = _json(body)
        assert snapshot["section_counts"] == {"layouts": 1}

        drifted = PersistedP6Layout(
            scope=scope,
            layout_scope="project",
            view_id="activity",
            revision=head.revision + 1,
            columns=head.columns,
            metadata={**original_metadata, "restore_probe": "drifted"},
        )
        repositories.layouts.upsert(drifted)
        assert repositories.layouts.get(scope, "project", "activity").metadata[
            "restore_probe"
        ] == "drifted"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot['snapshot_id']}/restore",
            body={
                "mode": "merge",
                "idempotency_key": "layout-restore-1",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:500]
        run = _json(body)
        assert run["run_id"] == "RSR-1"
        assert run["sections"] == {"layouts": {"created": 0, "updated": 1, "skipped": 0}}
        restored = repositories.layouts.get(scope, "project", "activity")
        assert dict(restored.metadata) == original_metadata
        assert restored.revision == drifted.revision + 1

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot['snapshot_id']}/restore",
            body={
                "mode": "merge",
                "idempotency_key": "layout-restore-2",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:500]
        assert _json(body)["sections"] == {
            "layouts": {"created": 0, "updated": 0, "skipped": 1}
        }

        status, body = _request(
            runtime.app, "GET", f"{BASE}/restores", cookie=admin.session_id
        )
        assert status == 200, body[:400]
        assert [item["run_id"] for item in _json(body)["runs"]] == ["RSR-2", "RSR-1"]
    finally:
        runtime.close()


def test_project_restore_is_additive_and_idempotent(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, body = _request(
            runtime.app,
            "POST",
            BASE,
            body={
                "kind": "project",
                "label": "Additive restore baseline",
                "idempotency_key": "additive-create",
            },
            cookie=admin.session_id,
        )
        assert status == 201, body[:500]
        snapshot_id = _json(body)["snapshot_id"]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={"mode": "merge", "idempotency_key": "additive-restore"},
            cookie=admin.session_id,
        )
        assert status == 200, body[:500]
        first = _json(body)
        assert first["replayed"] is False
        for section in ("wbs", "activities", "resources", "relationships"):
            assert first["sections"][section]["created"] == 0
            assert first["sections"][section]["updated"] == 0
            assert first["sections"][section]["skipped"] > 0

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={"mode": "merge", "idempotency_key": "additive-restore"},
            cookie=admin.session_id,
        )
        assert status == 200, body[:500]
        replay = _json(body)
        assert replay["replayed"] is True
        assert replay["run_id"] == first["run_id"]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={"mode": "overwrite", "idempotency_key": "additive-restore"},
            cookie=admin.session_id,
        )
        assert status == 409, body[:400]
        assert _json(body)["code"] == "BACKUP_IDEMPOTENCY_KEY_REUSE"

        status, body = _request(
            runtime.app,
            "POST",
            BASE,
            body={
                "kind": "project",
                "label": "Different label",
                "idempotency_key": "additive-create",
            },
            cookie=admin.session_id,
        )
        assert status == 409, body[:400]
        assert _json(body)["code"] == "BACKUP_IDEMPOTENCY_KEY_REUSE"
    finally:
        runtime.close()


def test_overwrite_restore_rewinds_an_edited_activity(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        from dataclasses import replace

        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        scope = _scope(runtime)
        repositories = PreviewRepositories.create(runtime.connection)
        activity = repositories.activities.list(scope)[0]
        original_name = activity.name

        status, body = _request(
            runtime.app,
            "POST",
            BASE,
            body={
                "kind": "project",
                "label": "Before edit",
                "idempotency_key": "rewind-create",
            },
            cookie=admin.session_id,
        )
        assert status == 201, body[:500]
        snapshot_id = _json(body)["snapshot_id"]

        repositories.activities.save(
            replace(activity, name="Edited after backup"),
            expected_revision=activity.record_revision,
        )
        edited = repositories.activities.get(scope, activity.activity_id)
        assert edited.name == "Edited after backup"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={
                "mode": "merge",
                "sections": ["activities"],
                "idempotency_key": "rewind-merge",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:500]
        merge = _json(body)["sections"]["activities"]
        assert merge["updated"] == 0 and merge["created"] == 0
        assert merge["skipped"] >= 1
        assert (
            repositories.activities.get(scope, activity.activity_id).name
            == "Edited after backup"
        )

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={
                "mode": "overwrite",
                "sections": ["activities"],
                "idempotency_key": "rewind-overwrite",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:500]
        overwrite = _json(body)
        assert overwrite["sections"]["activities"]["updated"] == 1
        assert set(overwrite["sections"]) == {"activities"}
        assert (
            repositories.activities.get(scope, activity.activity_id).name
            == original_name
        )
    finally:
        runtime.close()


def test_validation_and_missing_snapshots(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        for body, expected in (
            ({"kind": "project", "label": "", "idempotency_key": "x"}, "BACKUP_LABEL_REQUIRED"),
            ({"kind": "project", "label": "No key"}, "BACKUP_IDEMPOTENCY_KEY_REQUIRED"),
            ({"kind": "everything", "label": "K", "idempotency_key": "x"}, "INVALID_BACKUP_KIND"),
        ):
            status, payload = _request(
                runtime.app, "POST", BASE, body=body, cookie=admin.session_id
            )
            assert status == 400, payload[:400]
            assert _json(payload)["code"] == expected

        status, payload = _request(
            runtime.app, "GET", f"{BASE}/BKP-404", cookie=admin.session_id
        )
        assert status == 404, payload[:400]
        assert _json(payload)["code"] == "BACKUP_SNAPSHOT_NOT_FOUND"

        status, payload = _request(
            runtime.app,
            "POST",
            f"{BASE}/BKP-404/restore",
            body={"mode": "merge", "idempotency_key": "missing"},
            cookie=admin.session_id,
        )
        assert status == 404, payload[:400]

        status, payload = _request(
            runtime.app,
            "POST",
            BASE,
            body={
                "kind": "project",
                "label": "Valid",
                "idempotency_key": "valid-create",
            },
            cookie=admin.session_id,
        )
        assert status == 201, payload[:400]
        snapshot_id = _json(payload)["snapshot_id"]

        status, payload = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={"mode": "replace", "idempotency_key": "bad-mode"},
            cookie=admin.session_id,
        )
        assert status == 400, payload[:400]
        assert _json(payload)["code"] == "INVALID_RESTORE_MODE"

        status, payload = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={
                "mode": "merge",
                "sections": ["secrets"],
                "idempotency_key": "bad-section",
            },
            cookie=admin.session_id,
        )
        assert status == 400, payload[:400]
        assert _json(payload)["code"] == "BACKUP_SECTION_UNKNOWN"
    finally:
        runtime.close()


def test_backup_authorization_read_write_and_restore_gates(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])

        status, payload = _request(runtime.app, "GET", BASE, cookie=viewer.session_id)
        assert status == 200, payload[:400]

        status, payload = _request(
            runtime.app,
            "POST",
            BASE,
            body={"kind": "project", "label": "Denied", "idempotency_key": "viewer-1"},
            cookie=viewer.session_id,
        )
        assert status == 403, payload[:400]
        assert _json(payload)["code"] == "BACKUP_PERMISSION_DENIED"

        status, payload = _request(
            runtime.app,
            "POST",
            BASE,
            body={"kind": "project", "label": "Planner", "idempotency_key": "planner-1"},
            cookie=planner.session_id,
        )
        assert status == 201, payload[:400]
        snapshot_id = _json(payload)["snapshot_id"]

        status, payload = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={"mode": "merge", "idempotency_key": "planner-restore"},
            cookie=planner.session_id,
        )
        assert status == 403, payload[:400]
        assert _json(payload)["code"] == "BACKUP_PERMISSION_DENIED"

        status, payload = _request(
            runtime.app,
            "POST",
            f"{BASE}/{snapshot_id}/restore",
            body={"mode": "merge", "idempotency_key": "viewer-restore"},
            cookie=viewer.session_id,
        )
        assert status == 403, payload[:400]
    finally:
        runtime.close()
