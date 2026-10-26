from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import sqlite3

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_schedule_snapshot_publication_api import P6ScheduleSnapshotPublicationAPI
from construction_pm.project_schedule_settings_repository import (
    ProjectScheduleSettings,
    SQLiteProjectScheduleSettingsRepository,
)
from construction_pm.scheduling.authoritative_schedule import AuthoritativeScheduleMode
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling.calendar_system import CalendarSystem
from construction_pm.scheduling.schedule_options import ScheduleOptions
from construction_pm.scheduling.time_duration import DurationUnit


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self, revision: int = 2) -> None:
        self.revision = revision

    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("p1", tenant_id, "Project One", self.revision),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", self.revision)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str):
        return ProjectSummary(project_id, tenant_id, name, self.revision)


NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
SCOPE = BackendScope("t1", "p1", 2)


def _settings_repository(connection: sqlite3.Connection):
    return SQLiteProjectScheduleSettingsRepository(connection)


def _store_settings(
    repository: SQLiteProjectScheduleSettingsRepository,
    *,
    mode: AuthoritativeScheduleMode = AuthoritativeScheduleMode.DATE_BASED,
    data_date: date | None = date(2026, 10, 12),
) -> None:
    if mode is AuthoritativeScheduleMode.DATE_BASED:
        calendar = CalendarReference("CAL-1", "1", "working-day", CalendarSystem.GREGORIAN)
        start: date | datetime = date(2026, 9, 21)
    else:
        calendar = CalendarReference("CAL-1", "1", "working-time", CalendarSystem.GREGORIAN)
        start = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)
    repository.save(
        ProjectScheduleSettings(
            scope=SCOPE,
            mode=mode,
            project_calendar=calendar,
            project_start=start,
            schedule_options=ScheduleOptions(data_date=data_date),
            project_leveling_priority=10,
        )
    )


def _app(
    *,
    role: str = "project_admin",
    db_path: str = ":memory:",
    with_settings: bool = False,
    mode: AuthoritativeScheduleMode = AuthoritativeScheduleMode.DATE_BASED,
    data_date: date | None = date(2026, 10, 12),
    project_revision: int = 2,
):
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({role}), NOW + timedelta(hours=1)
    )
    policy = default_project_policy()
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(Sessions(session), Projects(project_revision), policy)
    )
    connection = sqlite3.connect(db_path)
    activity_repository = SQLiteActivityMasterRepository(connection)
    settings_repository = _settings_repository(connection)
    if with_settings:
        _store_settings(settings_repository, mode=mode, data_date=data_date)
    snapshot_api = P6ScheduleSnapshotPublicationAPI(
        publisher=object(),  # progress entry only resolves saved settings
        authorization_policy=policy,
        project_schedule_settings_repository=settings_repository,
    )
    routes = ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        p6_activity_master_api=P6ActivityMasterAPI(activity_repository, policy),
        p6_schedule_snapshot_api=snapshot_api,
    )
    return ProjectLifecycleWsgiApp(routes), activity_repository, connection


def _request(app, method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload or {}).encode("utf-8")
    status: list[str] = []
    chunks: list[bytes] = []
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_COOKIE": "cp_session=s1",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }

    def start_response(value, headers):
        status.append(value)

    chunks.extend(app(environ, start_response))
    return status[0], json.loads(b"".join(chunks))


def _create_activity(app, activity_id: str = "A-1", duration: str = "10") -> dict:
    status, created = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activities",
        {
            "contract_version": "p6-activity-master-api.v1",
            "activity_id": activity_id,
            "name": "Excavation",
            "duration_value": duration,
            "duration_unit": "working-day",
        },
    )
    assert status == "201 Created"
    return created


def _progress_path(activity_id: str = "A-1") -> str:
    return "/api/projects/p1/p6/activities/" + activity_id + "/progress"


def test_progress_entry_persists_valid_progress_and_completion(tmp_path):
    db_path = str(tmp_path / "progress.sqlite")
    app, _repository, connection = _app(db_path=db_path, with_settings=True)
    _create_activity(app)

    status, started = _request(
        app,
        "PATCH",
        _progress_path(),
        {
            "contract_version": "p6-activity-master-api.v1",
            "expected_revision": 1,
            "actual_start": "2026-10-07",
            "remaining_duration": 5,
            "percent_complete": 37.5,
        },
    )
    assert status == "200 OK"
    activity = started["activity"]
    assert activity["record_revision"] == 2
    assert activity["actual_start"] == "2026-10-07"
    assert activity["remaining_duration"] == 5
    assert activity["percent_complete"] == 37.5
    assert activity["status"] == "In Progress"
    assert activity["remaining_start"] is None

    # A separate connection proves the progress write is durable.
    fresh_connection = sqlite3.connect(db_path)
    persisted = SQLiteActivityMasterRepository(fresh_connection).get(SCOPE, "A-1")
    assert persisted is not None
    assert persisted.actual_start == date(2026, 10, 7)
    assert persisted.remaining_duration == 5
    assert persisted.percent_complete == 37.5
    assert persisted.status.value == "In Progress"
    fresh_connection.close()

    status, completed = _request(
        app,
        "PATCH",
        _progress_path(),
        {
            "contract_version": "p6-activity-master-api.v1",
            "expected_revision": 2,
            "actual_start": "2026-10-07",
            "actual_finish": "2026-10-12",
            "remaining_duration": 0,
        },
    )
    assert status == "200 OK"
    done = completed["activity"]
    assert done["record_revision"] == 3
    assert done["actual_finish"] == "2026-10-12"
    assert done["remaining_duration"] == 0
    # Completion normalizes the percent when the caller omits it.
    assert done["percent_complete"] == 100.0
    assert done["status"] == "Completed"
    connection.close()


def test_progress_entry_rejects_inconsistent_input_without_mutating_prior_data(tmp_path):
    db_path = str(tmp_path / "invalid-progress.sqlite")
    app, _repository, connection = _app(db_path=db_path, with_settings=True)
    _create_activity(app)

    base = {
        "contract_version": "p6-activity-master-api.v1",
        "expected_revision": 1,
    }
    cases = [
        ({"actual_start": "2026-10-07T09:00:00"}, "INVALID_ACTUAL_START"),
        ({"actual_start": "not-a-date"}, "INVALID_ACTUAL_START"),
        (
            {"actual_start": "2026-10-08", "actual_finish": "2026-10-07"},
            "PROGRESS_ACTUAL_FINISH_BEFORE_ACTUAL_START",
        ),
        ({"actual_finish": "2026-10-08"}, "PROGRESS_ACTUAL_FINISH_REQUIRES_ACTUAL_START"),
        (
            {"actual_start": "2026-10-13", "remaining_duration": 4},
            "PROGRESS_ACTUAL_START_AFTER_DATA_DATE",
        ),
        (
            {"actual_start": "2026-10-07", "actual_finish": "2026-10-13"},
            "PROGRESS_ACTUAL_FINISH_AFTER_DATA_DATE",
        ),
        ({"remaining_duration": 4}, "PROGRESS_ACTUAL_START_REQUIRED"),
        ({"percent_complete": 40}, "PROGRESS_ACTUAL_START_REQUIRED"),
        (
            {"actual_start": "2026-10-07", "remaining_duration": 0},
            "PROGRESS_ACTUAL_FINISH_REQUIRED_FOR_COMPLETION",
        ),
        (
            {"actual_start": "2026-10-07", "percent_complete": 100},
            "PROGRESS_ACTUAL_FINISH_REQUIRED_FOR_COMPLETION",
        ),
        (
            {"actual_start": "2026-10-07", "percent_complete": 150},
            "INVALID_PERCENT_COMPLETE",
        ),
        (
            {"actual_start": "2026-10-07", "actual_finish": "2026-10-08", "remaining_duration": 3},
            "PROGRESS_COMPLETED_ACTIVITY_REMAINING_DURATION",
        ),
        (
            {"actual_start": "2026-10-07", "actual_finish": "2026-10-08", "percent_complete": 80},
            "PROGRESS_COMPLETED_ACTIVITY_PERCENT_COMPLETE",
        ),
        ({"data_date": "2026-10-20"}, "PROGRESS_REQUEST_FIELDS_INVALID"),
    ]
    for changes, expected_code in cases:
        status, error = _request(app, "PATCH", _progress_path(), {**base, **changes})
        assert status == "400 Bad Request", (changes, status, error)
        assert error["code"] == expected_code, (changes, error)

    status, loaded = _request(app, "GET", "/api/projects/p1/p6/activities/A-1")
    assert status == "200 OK"
    activity = loaded["activity"]
    assert activity["record_revision"] == 1
    assert activity["actual_start"] is None
    assert activity["actual_finish"] is None
    assert activity["remaining_duration"] is None
    assert activity["percent_complete"] is None
    connection.close()


def test_stale_progress_revision_is_rejected_without_corrupting_current_progress(tmp_path):
    app, _repository, connection = _app(db_path=str(tmp_path / "stale-progress.sqlite"), with_settings=True)
    _create_activity(app)

    status, _started = _request(
        app,
        "PATCH",
        _progress_path(),
        {
            "expected_revision": 1,
            "actual_start": "2026-10-07",
            "remaining_duration": 5,
            "percent_complete": 50,
        },
    )
    assert status == "200 OK"

    status, conflict = _request(
        app,
        "PATCH",
        _progress_path(),
        {
            "expected_revision": 1,
            "actual_start": "2026-10-01",
            "remaining_duration": 9,
            "percent_complete": 10,
        },
    )
    assert status == "409 Conflict"
    assert conflict["code"] == "REVISION_CONFLICT"

    status, loaded = _request(app, "GET", "/api/projects/p1/p6/activities/A-1")
    assert status == "200 OK"
    assert loaded["activity"]["record_revision"] == 2
    assert loaded["activity"]["actual_start"] == "2026-10-07"
    assert loaded["activity"]["remaining_duration"] == 5
    assert loaded["activity"]["percent_complete"] == 50
    connection.close()


def test_progress_entry_requires_saved_date_based_settings_with_data_date():
    no_settings_app, _repository, connection = _app()
    _create_activity(no_settings_app)
    status, error = _request(
        no_settings_app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 1, "actual_start": "2026-10-07"},
    )
    assert status == "400 Bad Request"
    assert error["code"] == "PROJECT_SCHEDULE_SETTINGS_REQUIRED"
    connection.close()

    time_aware_app, _repository, connection = _app(
        with_settings=True,
        mode=AuthoritativeScheduleMode.TIME_AWARE,
        data_date=None,
    )
    _create_activity(time_aware_app)
    status, error = _request(
        time_aware_app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 1, "actual_start": "2026-10-07"},
    )
    assert status == "400 Bad Request"
    assert error["code"] == "TIME_AWARE_PROGRESS_ENTRY_NOT_AVAILABLE"
    connection.close()

    no_data_date_app, _repository, connection = _app(
        with_settings=True,
        data_date=None,
    )
    _create_activity(no_data_date_app)
    status, error = _request(
        no_data_date_app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 1, "actual_start": "2026-10-07"},
    )
    assert status == "400 Bad Request"
    assert error["code"] == "DATE_BASED_DATA_DATE_REQUIRED"
    connection.close()


def test_viewer_is_denied_progress_entry_and_generic_progress_edit(tmp_path):
    app, repository, connection = _app(
        role="viewer", db_path=str(tmp_path / "viewer-progress.sqlite"), with_settings=True
    )
    repository.save(
        ActivityMaster(
            scope=SCOPE,
            activity_id="A-1",
            duration_value=Decimal("10"),
            duration_unit=DurationUnit("working-day"),
            name="Excavation",
        ),
        expected_revision=0,
    )

    status, error = _request(
        app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 1, "actual_start": "2026-10-07"},
    )
    assert status == "403 Forbidden"
    assert error["code"] == "authorization denied for permission=project.write"

    status, error = _request(
        app,
        "PATCH",
        "/api/projects/p1/p6/activities/A-1",
        {
            "expected_revision": 1,
            "actual_start": "2026-10-07",
            "remaining_duration": 5,
        },
    )
    assert status == "403 Forbidden"
    connection.close()


def test_generic_activity_patch_cannot_bypass_progress_invariants(tmp_path):
    app, _repository, connection = _app(
        db_path=str(tmp_path / "generic-patch-progress.sqlite"), with_settings=True
    )
    _create_activity(app)

    status, error = _request(
        app,
        "PATCH",
        "/api/projects/p1/p6/activities/A-1",
        {
            "expected_revision": 1,
            "actual_finish": "2026-10-08",
        },
    )
    assert status == "400 Bad Request"
    assert error["code"] == "PROGRESS_ACTUAL_FINISH_REQUIRES_ACTUAL_START"

    status, error = _request(
        app,
        "PATCH",
        "/api/projects/p1/p6/activities/A-1",
        {
            "expected_revision": 1,
            "actual_start": "2026-10-07",
            "actual_finish": "2026-10-08",
            "remaining_duration": 4,
        },
    )
    assert status == "400 Bad Request"
    assert error["code"] == "PROGRESS_COMPLETED_ACTIVITY_REMAINING_DURATION"

    status, loaded = _request(app, "GET", "/api/projects/p1/p6/activities/A-1")
    assert status == "200 OK"
    assert loaded["activity"]["record_revision"] == 1
    assert loaded["activity"]["actual_start"] is None
    connection.close()


def test_progress_entry_preserves_recorded_actuals_when_fields_are_omitted(tmp_path):
    app, _repository, connection = _app(
        db_path=str(tmp_path / "preserve-progress.sqlite"), with_settings=True
    )
    _create_activity(app)

    status, _ = _request(
        app,
        "PATCH",
        _progress_path(),
        {
            "expected_revision": 1,
            "actual_start": "2026-10-07",
            "actual_finish": "2026-10-09",
        },
    )
    assert status == "200 OK"

    # Omitting the finish must not silently reopen the completed activity.
    status, error = _request(
        app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 2, "remaining_duration": 4},
    )
    assert status == "400 Bad Request"
    assert error["code"] == "PROGRESS_COMPLETED_ACTIVITY_REMAINING_DURATION"

    # A progress observation that only omits the finish keeps both actuals and
    # the completed state unchanged.
    status, unchanged = _request(
        app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 2, "percent_complete": 100},
    )
    assert status == "200 OK"
    assert unchanged["activity"]["actual_start"] == "2026-10-07"
    assert unchanged["activity"]["actual_finish"] == "2026-10-09"
    assert unchanged["activity"]["status"] == "Completed"
    assert unchanged["activity"]["record_revision"] == 3

    # Reopening is explicit: the caller clears the finish and supplies the new
    # remaining work in the same request.
    status, reopened = _request(
        app,
        "PATCH",
        _progress_path(),
        {
            "expected_revision": 3,
            "actual_finish": None,
            "remaining_duration": 4,
            "percent_complete": 60,
        },
    )
    assert status == "200 OK"
    assert reopened["activity"]["actual_start"] == "2026-10-07"
    assert reopened["activity"]["actual_finish"] is None
    assert reopened["activity"]["remaining_duration"] == 4
    assert reopened["activity"]["percent_complete"] == 60
    assert reopened["activity"]["status"] == "In Progress"
    connection.close()


def test_generic_activity_patch_cannot_store_date_based_actuals_beyond_data_date(tmp_path):
    app, _repository, connection = _app(
        db_path=str(tmp_path / "generic-actuals.sqlite"), with_settings=True
    )
    _create_activity(app)

    status, error = _request(
        app,
        "PATCH",
        "/api/projects/p1/p6/activities/A-1",
        {"expected_revision": 1, "actual_start": "2026-10-13"},
    )
    assert status == "400 Bad Request"
    assert error["code"] == "PROGRESS_ACTUAL_START_AFTER_DATA_DATE"

    # DATE_BASED progress has no timezone, so a time-bearing instant is not a
    # valid recorded date even through the general edit route.
    status, error = _request(
        app,
        "PATCH",
        "/api/projects/p1/p6/activities/A-1",
        {"expected_revision": 1, "actual_start": "2026-10-07T09:00:00"},
    )
    assert status == "400 Bad Request"
    assert error["code"] == "INVALID_ACTUAL_START"

    status, loaded = _request(app, "GET", "/api/projects/p1/p6/activities/A-1")
    assert status == "200 OK"
    assert loaded["activity"]["record_revision"] == 1
    assert loaded["activity"]["actual_start"] is None
    connection.close()


def test_progress_entry_maps_saved_settings_revision_conflict_to_409(tmp_path):
    # The project is at revision 3, but its saved schedule settings belong to
    # revision 2. The Data Date read must fail closed with a conflict instead of
    # silently using settings from another revision.
    app, _repository, connection = _app(
        db_path=str(tmp_path / "settings-revision-progress.sqlite"),
        with_settings=True,
        project_revision=3,
    )
    _create_activity(app)

    status, error = _request(
        app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 1, "actual_start": "2026-10-07"},
    )
    assert status == "409 Conflict"
    assert error["code"] == "REVISION_CONFLICT"

    status, loaded = _request(app, "GET", "/api/projects/p1/p6/activities/A-1")
    assert status == "200 OK"
    assert loaded["activity"]["record_revision"] == 1
    assert loaded["activity"]["actual_start"] is None
    connection.close()


def test_progress_entry_maps_tampered_settings_to_integrity_failure(tmp_path):
    app, _repository, connection = _app(
        db_path=str(tmp_path / "tampered-settings-progress.sqlite"),
        with_settings=True,
    )
    _create_activity(app)
    connection.execute(
        "UPDATE project_schedule_settings SET canonical_payload=?",
        ('{"mode":"DATE_BASED"}',),
    )
    connection.commit()

    status, error = _request(
        app,
        "PATCH",
        _progress_path(),
        {"expected_revision": 1, "actual_start": "2026-10-07"},
    )
    assert status == "500 Internal Server Error"
    assert error["code"] == "SETTINGS_HASH_MISMATCH"
    assert error["retryable"] is False
    connection.close()
