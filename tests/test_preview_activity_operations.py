from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"
OPERATIONS_PATH = f"/api/projects/{RPS_PROJECT}/p6/activity-operations"
ACTIVITIES_PATH = f"/api/projects/{RPS_PROJECT}/p6/activities"
CONTRACT = "p6-activity-operations.v1"


def _request(
    app,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    cookie: str | None = None,
    idempotency_key: str | None = None,
):
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    if body:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    if idempotency_key is not None:
        environ["HTTP_IDEMPOTENCY_KEY"] = idempotency_key
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _operation(app, cookie: str, payload: dict, key: str | None):
    return _request(
        app,
        "POST",
        OPERATIONS_PATH,
        cookie=cookie,
        body=json.dumps({"contract_version": CONTRACT, **payload}).encode(),
        idempotency_key=key,
    )


def _activity(app, cookie: str, activity_id: str) -> dict:
    status, body = _request(app, "GET", ACTIVITIES_PATH, cookie=cookie)
    assert status == 200, body[:300]
    return next(
        item["activity"]
        for item in json.loads(body)["activities"]
        if item["activity"]["activity_id"] == activity_id
    )


def _wbs_of(app, cookie: str, activity_id: str) -> str:
    # The activity read model exposes the WBS assignment the service wrote.
    return _activity(app, cookie, activity_id)["wbs_id"]


def test_preview_copy_paste_is_transactional_idempotent_and_revision_guarded(tmp_path: Path) -> None:
    database = tmp_path / "preview.sqlite3"
    runtime = open_preview_runtime(database, reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        a120 = _activity(runtime.app, planner.session_id, "A120")
        a130 = _activity(runtime.app, planner.session_id, "A130")
        assert _wbs_of(runtime.app, planner.session_id, "A120") == "WBS-RPS-CIVIL"

        status, body = _operation(
            runtime.app,
            planner.session_id,
            {
                "operation": "copy",
                "activity_ids": ["A120", "A130"],
                "target_wbs_id": "WBS-RPS-CIVIL",
                "expected_revisions": {
                    "A120": a120["record_revision"],
                    "A130": a130["record_revision"],
                },
            },
            "preview-copy-1",
        )
        assert status == 200, body[:400]
        copied = json.loads(body)
        assert copied["operation"] == "copy"
        mapping = {item["source_activity_id"]: item["activity_id"] for item in copied["created"]}
        assert mapping == {"A120": "A120-COPY", "A130": "A130-COPY"}
        # The internal relationship is copied with fresh ids; external links are
        # reported as skipped instead of being silently re-pointed.
        assert copied["relationships_created"] == ["REL-RPS-120-COPY"]
        assert all(item["reason"] == "EXTERNAL_ENDPOINT" for item in copied["relationships_skipped"])
        copied_activity = _activity(runtime.app, planner.session_id, "A120-COPY")
        assert copied_activity["record_revision"] == 1
        assert _wbs_of(runtime.app, planner.session_id, "A120-COPY") == "WBS-RPS-CIVIL"

        # The same reservation replays the original result instead of copying twice.
        status, replay_body = _operation(
            runtime.app,
            planner.session_id,
            {
                "operation": "copy",
                "activity_ids": ["A120", "A130"],
                "target_wbs_id": "WBS-RPS-CIVIL",
                "expected_revisions": {
                    "A120": a120["record_revision"],
                    "A130": a130["record_revision"],
                },
            },
            "preview-copy-1",
        )
        assert status == 200, replay_body[:300]
        replay = json.loads(replay_body)
        assert replay["replayed"] is True
        assert replay["operation_id"] == copied["operation_id"]

        # A stale revision is rejected before any row is written.
        status, conflict = _operation(
            runtime.app,
            planner.session_id,
            {
                "operation": "copy",
                "activity_ids": ["A120"],
                "expected_revisions": {"A120": a120["record_revision"] + 1},
            },
            "preview-copy-stale",
        )
        assert status == 409, conflict[:300]
        assert json.loads(conflict)["code"] == "REVISION_CONFLICT"

        # Missing idempotency keys are refused outright.
        status, missing = _operation(
            runtime.app,
            planner.session_id,
            {"operation": "copy", "activity_ids": ["A120"]},
            None,
        )
        assert status == 400, missing[:300]
        assert json.loads(missing)["code"] == "IDEMPOTENCY_KEY_REQUIRED"

        # Reopen the same database: the copies are persisted project facts.
        reopened = open_preview_runtime(database, reset=False)
        try:
            session = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            assert _activity(reopened.app, session.session_id, "A130-COPY")["activity_id"] == "A130-COPY"
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_viewer_cannot_copy_and_delete_needs_dependency_confirmation(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        a120 = _activity(runtime.app, planner.session_id, "A120")
        status, denied = _operation(
            runtime.app,
            viewer.session_id,
            {
                "operation": "copy",
                "activity_ids": ["A120"],
                "expected_revisions": {"A120": a120["record_revision"]},
            },
            "viewer-copy",
        )
        assert status == 403, denied[:300]
        assert json.loads(denied)["code"].startswith("AUTHORIZATION")

        # A120 owns REL-RPS-120 (A120→A130) and REL-RPS-110 (A110→A120), so the
        # first delete must ask for explicit dependency confirmation.
        status, confirmation = _operation(
            runtime.app,
            planner.session_id,
            {
                "operation": "delete",
                "activity_ids": ["A120"],
                "expected_revisions": {"A120": a120["record_revision"]},
            },
            "delete-a120",
        )
        assert status == 409, confirmation[:400]
        body = json.loads(confirmation)
        assert body["code"] == "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED"
        assert body["details"]["relationships"] == 2

        status, deleted = _operation(
            runtime.app,
            planner.session_id,
            {
                "operation": "delete",
                "activity_ids": ["A120"],
                "confirm_dependencies": True,
                "expected_revisions": {"A120": a120["record_revision"]},
            },
            "delete-a120-confirmed",
        )
        assert status == 200, deleted[:400]
        assert json.loads(deleted)["deleted"] == ["A120"]

        status, gone = _request(
            runtime.app, "GET", f"{ACTIVITIES_PATH}/A120", cookie=planner.session_id
        )
        assert status == 404, gone[:300]
        # The relationships that referenced A120 were removed with it; A130 stays.
        assert _activity(runtime.app, planner.session_id, "A130")["activity_id"] == "A130"
    finally:
        runtime.close()


def test_preview_cut_paste_moves_the_activity_between_wbs_bands(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        a140 = _activity(runtime.app, planner.session_id, "A140")
        assert _wbs_of(runtime.app, planner.session_id, "A140") == "WBS-RPS-CIVIL"
        status, body = _operation(
            runtime.app,
            planner.session_id,
            {
                "operation": "move",
                "activity_ids": ["A140"],
                "target_wbs_id": "WBS-RPS-PM",
                "expected_revisions": {"A140": a140["record_revision"]},
            },
            "cut-a140",
        )
        assert status == 200, body[:400]
        assert json.loads(body)["moved"] == ["A140"]
        assert _wbs_of(runtime.app, planner.session_id, "A140") == "WBS-RPS-PM"

        # A move needs a real target band; the server refuses an empty one.
        status, missing_target = _operation(
            runtime.app,
            planner.session_id,
            {"operation": "move", "activity_ids": ["A140"]},
            "cut-a140-no-target",
        )
        assert status == 400, missing_target[:300]
        assert json.loads(missing_target)["code"] == "P6_ACTIVITY_TARGET_WBS_REQUIRED"
    finally:
        runtime.close()
