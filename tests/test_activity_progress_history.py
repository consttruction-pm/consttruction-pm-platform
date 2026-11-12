from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest

from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.activity_progress_history import (
    ActivityProgressEvent,
    ProgressFieldChange,
    ProgressHistoryPersistenceError,
    ProgressOutOfSequenceFinding,
    SQLiteActivityProgressHistoryRepository,
    diff_progress_fields,
    evaluate_out_of_sequence,
)
from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    RoleBasedAuthorizationPolicy,
    default_role_permissions,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_activity_progress_api import (
    P6_ACTIVITY_PROGRESS_HISTORY_API_VERSION,
    P6ActivityProgressAPI,
)
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.activity import (
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


SCOPE = BackendScope("tenant-progress", "project-progress", 4)
NOW = datetime(2026, 11, 12, 8, 30, tzinfo=timezone.utc)


def _activity(**overrides) -> ActivityMaster:
    payload = dict(
        scope=SCOPE,
        activity_id="A100",
        duration_value=Decimal("5"),
        duration_unit=DurationUnit.WORKING_DAY,
        name="Pour foundation",
        percent_complete_type=PercentCompleteType.DURATION,
        activity_type=ActivityType.TASK_DEPENDENT,
    )
    payload.update(overrides)
    return ActivityMaster(**payload)


def _event(**overrides) -> ActivityProgressEvent:
    payload = dict(
        scope=SCOPE,
        event_id="A100@2",
        activity_id="A100",
        recorded_at=NOW,
        actor_user_id="user-planner",
        from_record_revision=1,
        to_record_revision=2,
        changes=(ProgressFieldChange("percent_complete", None, "25.0"),),
    )
    payload.update(overrides)
    return ActivityProgressEvent(**payload)


def test_progress_history_repository_appends_lists_and_replays_idempotently() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteActivityProgressHistoryRepository(connection)
    stored = repository.append(_event())
    assert stored.event_id == "A100@2"
    assert stored.changes[0].after == "25.0"

    # The same event id is an immutable replay, not a duplicate or an update.
    replay = repository.append(_event(changes=(ProgressFieldChange("percent_complete", None, "90.0"),)))
    assert replay.changes[0].after == "25.0"
    assert len(repository.list(SCOPE, "A100")) == 1

    repository.append(
        _event(
            event_id="A100@3",
            to_record_revision=3,
            from_record_revision=2,
            changes=(ProgressFieldChange("status", "In Progress", "Completed"),),
            findings=(
                ProgressOutOfSequenceFinding(
                    "FS_PREDECESSOR_NOT_FINISHED", "REL-1", "A090", "FS"
                ),
            ),
        )
    )
    events = repository.list(SCOPE, "A100")
    assert [item.event_id for item in events] == ["A100@2", "A100@3"]
    assert repository.latest(SCOPE, "A100") == events[-1]
    assert events[-1].out_of_sequence is True
    assert repository.list(SCOPE, "A999") == ()
    connection.close()


def test_progress_event_validation_rejects_untracked_or_empty_changes() -> None:
    with pytest.raises(ProgressHistoryPersistenceError):
        ProgressFieldChange("name", "Before", "After").validate()
    with pytest.raises(ProgressHistoryPersistenceError):
        ProgressFieldChange("status", "In Progress", "In Progress").validate()
    with pytest.raises(ProgressHistoryPersistenceError):
        _event(recorded_at=datetime(2026, 11, 12, 8, 30)).validate()
    with pytest.raises(ProgressHistoryPersistenceError):
        _event(to_record_revision=1).validate()


def test_diff_progress_fields_ignores_non_progress_edits() -> None:
    previous = _activity()
    renamed = _activity(name="Renamed activity")
    assert diff_progress_fields(previous, renamed) == ()

    progressed = _activity(
        percent_complete=40.0,
        actual_start=date(2026, 11, 2),
        remaining_duration=3,
        status=ActivityStatus.IN_PROGRESS,
        status_code=ActivityStatusCode.ACTIVE,
    )
    changes = {item.field: item for item in diff_progress_fields(previous, progressed)}
    assert set(changes) == {
        "percent_complete",
        "actual_start",
        "remaining_duration",
        "status",
        "status_code",
    }
    assert changes["actual_start"].after == "2026-11-02"
    assert changes["percent_complete"].after == "40.0"


def test_out_of_sequence_review_compares_actual_dates_to_stored_logic() -> None:
    predecessor = _activity(
        activity_id="A090",
        actual_start=date(2026, 10, 20),
        actual_finish=date(2026, 10, 25),
        status=ActivityStatus.COMPLETED,
        status_code=ActivityStatusCode.INACTIVE,
    )
    relationships = (
        RelationshipMaster(SCOPE, "REL-FS", "A090", "A100", RelationshipType.FS),
        RelationshipMaster(SCOPE, "REL-SS", "A090", "A100", RelationshipType.SS),
        RelationshipMaster(SCOPE, "REL-FF", "A090", "A100", RelationshipType.FF),
    )
    started_early = _activity(
        actual_start=date(2026, 10, 22),
        actual_finish=date(2026, 10, 24),
    )
    findings = evaluate_out_of_sequence(
        started_early, relationships, (predecessor, started_early)
    )
    codes = {(item.relationship_id, item.code) for item in findings}
    # FS: started three days after the predecessor started but before it
    # finished. SS: started after the predecessor started, so it is in sequence.
    # FF: finished before the predecessor finished.
    assert codes == {
        ("REL-FS", "FS_START_BEFORE_PREDECESSOR_FINISH"),
        ("REL-FF", "FF_FINISH_BEFORE_PREDECESSOR_FINISH"),
    }

    not_finished = evaluate_out_of_sequence(
        _activity(actual_start=date(2026, 10, 26)),
        (relationships[0],),
        (_activity(activity_id="A090"),),
    )
    assert [item.code for item in not_finished] == ["FS_PREDECESSOR_NOT_FINISHED"]


def _api(tmp_path: Path) -> tuple[P6ActivityProgressAPI, SQLiteActivityProgressHistoryRepository, AuthorizationContext]:
    connection = sqlite3.connect(tmp_path / "history.sqlite3")
    wbs_free = ActivityMaster(
        scope=SCOPE,
        activity_id="A100",
        duration_value=Decimal("5"),
        duration_unit=DurationUnit.WORKING_DAY,
        name="Pour foundation",
    )
    from construction_pm.activity_master_repository import SQLiteActivityMasterRepository

    activities = SQLiteActivityMasterRepository(connection)
    activities.save(wbs_free)
    relationships = SQLiteRelationshipMasterRepository(connection)
    history = SQLiteActivityProgressHistoryRepository(connection)
    policy = RoleBasedAuthorizationPolicy(default_role_permissions())
    api = P6ActivityProgressAPI(
        activity_api=P6ActivityMasterAPI(activities, policy),
        history_repository=history,
        authorization_policy=policy,
        relationship_repository=relationships,
        activity_repository=activities,
        transaction_manager=SQLiteTransactionManager(connection),
        clock=lambda: NOW,
    )
    auth = AuthorizationContext(
        SCOPE.tenant_id, SCOPE.project_id, "user-planner", frozenset({"planner"})
    )
    return api, history, auth


def test_progress_api_records_history_in_the_same_write(tmp_path: Path) -> None:
    api, history, auth = _api(tmp_path)
    updated = api.update(
        _activity(
            percent_complete=25.0,
            actual_start=date(2026, 11, 2),
            remaining_duration=4,
            status=ActivityStatus.IN_PROGRESS,
            status_code=ActivityStatusCode.ACTIVE,
        ),
        expected_revision=1,
        auth_context=auth,
    )
    assert updated["activity"]["record_revision"] == 2

    events = history.list(SCOPE, "A100")
    assert len(events) == 1
    event = events[0]
    assert event.event_id == "A100@2"
    assert event.from_record_revision == 1
    assert event.to_record_revision == 2
    assert event.actor_user_id == "user-planner"
    assert event.recorded_at == NOW
    assert {item.field for item in event.changes} == {
        "percent_complete",
        "actual_start",
        "remaining_duration",
        "status",
        "status_code",
    }

    payload = api.history(SCOPE, "A100", auth_context=auth)
    assert payload is not None
    assert payload["contract_version"] == P6_ACTIVITY_PROGRESS_HISTORY_API_VERSION
    assert payload["kind"] == "p6_activity_progress_history"
    assert payload["percent_complete_trend"] == [
        {
            "to_record_revision": 2,
            "recorded_at": NOW.isoformat(),
            "percent_complete": "25.0",
        }
    ]
    assert payload["out_of_sequence_review"]["evaluated_event_id"] == "A100@2"
    assert payload["out_of_sequence_review"]["is_out_of_sequence"] is False


def test_progress_api_does_not_log_a_non_progress_edit(tmp_path: Path) -> None:
    api, history, auth = _api(tmp_path)
    api.update(
        _activity(name="Renamed foundation pour"),
        expected_revision=1,
        auth_context=auth,
    )
    assert history.list(SCOPE, "A100") == ()
    payload = api.history(SCOPE, "A100", auth_context=auth)
    assert payload is not None
    assert payload["events"] == []
    assert payload["out_of_sequence_review"] is None
    assert api.history(SCOPE, "A999", auth_context=auth) is None


def test_progress_api_enforces_permissions_and_revision_conflicts(tmp_path: Path) -> None:
    api, history, _ = _api(tmp_path)
    viewer = AuthorizationContext(
        SCOPE.tenant_id, SCOPE.project_id, "user-viewer", frozenset({"viewer"})
    )
    with pytest.raises(AuthorizationError):
        api.update(_activity(percent_complete=10.0), expected_revision=1, auth_context=viewer)
    # A viewer can still read the empty history.
    payload = api.history(SCOPE, "A100", auth_context=viewer)
    assert payload is not None and payload["events"] == []

    planner = AuthorizationContext(
        SCOPE.tenant_id, SCOPE.project_id, "user-planner", frozenset({"planner"})
    )
    with pytest.raises(Exception) as conflict:
        api.update(_activity(percent_complete=10.0), expected_revision=9, auth_context=planner)
    assert "REVISION_CONFLICT" in str(conflict.value)
    assert history.list(SCOPE, "A100") == ()


# --- HTTP seam -----------------------------------------------------------------


RPS_PROJECT = "preview-rps-01"
ACTIVITY_PATH = f"/api/projects/{RPS_PROJECT}/p6/activities"


def _request(app, method: str, path: str, *, body: bytes = b"", cookie: str | None = None):
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
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def test_preview_patch_records_progress_history_and_out_of_sequence_review(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        payload = {
            "contract_version": "p6-activity-master-api.v1",
            "expected_revision": 1,
            "percent_complete": 20,
            "actual_start": "2026-10-07",
            "actual_finish": None,
            "remaining_duration": 6,
            "status": "In Progress",
        }
        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=planner.session_id,
            body=json.dumps(payload).encode(),
        )
        assert status == 200, body[:300]

        status, body = _request(
            runtime.app,
            "GET",
            f"{ACTIVITY_PATH}/A140/progress-history",
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        history = json.loads(body)
        assert history["contract_version"] == "p6-activity-progress-history-api.v1"
        assert history["kind"] == "p6_activity_progress_history"
        assert history["activity_id"] == "A140"
        assert len(history["events"]) == 1
        event = history["events"][0]
        assert event["event_id"] == "A140@2"
        assert event["actor_user_id"] == "preview-planner"
        assert {item["field"] for item in event["changes"]} == {
            "actual_start",
            "percent_complete",
            "remaining_duration",
            "status",
        }
        # A140 has an FS predecessor (A130) that has not finished, so recording
        # an actual start is an out-of-sequence update against stored logic.
        assert event["out_of_sequence"]["is_out_of_sequence"] is True
        assert {
            item["code"] for item in event["out_of_sequence"]["findings"]
        } == {"FS_PREDECESSOR_NOT_FINISHED"}
        assert history["percent_complete_trend"][0]["percent_complete"] == "20.0"
        assert history["out_of_sequence_review"]["evaluated_event_id"] == "A140@2"

        # Reopening keeps the append-only history.
        runtime.close()
        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
            status, body = _request(
                reopened.app,
                "GET",
                f"{ACTIVITY_PATH}/A140/progress-history",
                cookie=reader.session_id,
            )
            assert status == 200
            assert len(json.loads(body)["events"]) == 1
        finally:
            reopened.close()
            runtime = None
    finally:
        if runtime is not None:
            runtime.close()


def test_preview_progress_history_permissions_and_not_found(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app,
            "GET",
            f"{ACTIVITY_PATH}/A140/progress-history",
            cookie=viewer.session_id,
        )
        assert status == 200
        assert json.loads(body)["events"] == []

        status, body = _request(
            runtime.app,
            "GET",
            f"{ACTIVITY_PATH}/A999/progress-history",
            cookie=viewer.session_id,
        )
        assert status == 404
        assert json.loads(body)["code"] == "P6_ACTIVITY_PROGRESS_HISTORY_NOT_FOUND"
    finally:
        runtime.close()
