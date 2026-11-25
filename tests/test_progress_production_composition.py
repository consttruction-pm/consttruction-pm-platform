"""Data Date and Progress are operational only when the seam wires them.

The Progress window in production reads ``GET .../p6/activities/{id}/progress-
history`` and writes every progress-bearing edit through ``PATCH
.../p6/activities/{id}``. Both routes are served by ``P6ActivityProgressAPI``,
which only exists when ``build_project_lifecycle_wsgi_app`` receives the
append-only history repository *and* the transaction manager. Before this
slice the production runtime supplied neither, so:
  * the history route answered ``P6_ACTIVITY_PROGRESS_HISTORY_UNAVAILABLE``,
  * and PATCH silently skipped the immutable progress event.

These tests pin both directions of the seam: an unwired application exposes
the gap, and a wired application records, serves and conflict-checks real
progress over the HTTP contract.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import sqlite3

import pytest

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.activity_progress_history import (
    SQLiteActivityProgressHistoryRepository,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.production_composition import build_project_lifecycle_wsgi_app
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
)
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


SCOPE = BackendScope("T-1", "P-1", 9)
NOW = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)


class _Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class _Projects:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("P-1", tenant_id, "Project One", 9),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "P-1":
            return None
        return ProjectSummary("P-1", tenant_id, "Project One", 9)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def _lifecycle_api(
    permissions: frozenset[str], *, tenant_id: str = "T-1"
) -> ProjectLifecycleAPI:
    session = AuthenticatedSession(
        "s1", "u1", tenant_id, permissions, NOW + timedelta(hours=1)
    )
    service = ProjectLifecycleService(
        _Sessions(session), _Projects(tenant_id), default_project_policy()
    )
    return ProjectLifecycleAPI(service)


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
    chunks.extend(app(environ, lambda value, headers: status.append(value)))
    return status[0], json.loads(b"".join(chunks))


def _seed(connection: sqlite3.Connection) -> None:
    activities = SQLiteActivityMasterRepository(connection)
    # Predecessor already finished on 25 Oct; the successor's actual start is
    # recorded after it, which the FS review must flag.
    activities.save(
        ActivityMaster(
            scope=SCOPE,
            activity_id="A-0",
            duration_value=Decimal("3"),
            duration_unit=DurationUnit.WORKING_DAY,
            actual_start=date(2026, 10, 20),
            actual_finish=date(2026, 10, 25),
            name="Mobilise",
        )
    )
    activities.save(
        ActivityMaster(
            scope=SCOPE,
            activity_id="A-1",
            duration_value=Decimal("5"),
            duration_unit=DurationUnit.WORKING_DAY,
            name="Excavate",
        )
    )
    SQLiteRelationshipMasterRepository(connection).save(
        RelationshipMaster(
            scope=SCOPE,
            relationship_id="REL-1",
            predecessor_id="A-0",
            successor_id="A-1",
            relationship_type=RelationshipType.FS,
        )
    )


def _app(
    connection: sqlite3.Connection,
    *,
    wire_progress: bool,
    permissions: frozenset[str] = frozenset({"project_admin"}),
    tenant_id: str = "T-1",
):
    _seed(connection)
    manager = SQLiteTransactionManager(connection)
    options: dict[str, object] = {
        "activity_master_repository": SQLiteActivityMasterRepository(connection),
        "relationship_master_repository": SQLiteRelationshipMasterRepository(connection),
    }
    if wire_progress:
        options.update(
            activity_progress_history_repository=SQLiteActivityProgressHistoryRepository(
                connection
            ),
            activity_progress_transaction_manager=manager,
        )
    return build_project_lifecycle_wsgi_app(
        lifecycle_api=_lifecycle_api(permissions, tenant_id=tenant_id),
        snapshot_repository=SQLiteScheduleInputSnapshotRepository(connection),
        calendar_registry_factory=lambda: CalendarResolverRegistry(day_resolvers={}),
        calculation_context_repository=SQLiteCalculationContextRepository(connection),
        authorization_policy=default_project_policy(),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        **options,
    )


def _progress_patch() -> dict:
    return {
        "expected_revision": 1,
        "actual_start": "2026-10-22",
        "percent_complete": 40.0,
        "remaining_duration": 3,
        "status": "In Progress",
        "status_code": "Active",
    }


def test_unwired_composition_exposes_the_progress_gap():
    connection = sqlite3.connect(":memory:")
    app = _app(connection, wire_progress=False)

    status, body = _request(
        app, "GET", "/api/projects/P-1/p6/activities/A-1/progress-history"
    )
    assert status.startswith("400"), body
    assert body["code"] == "P6_ACTIVITY_PROGRESS_HISTORY_UNAVAILABLE"

    # The PATCH still saves through the activity master API, but nothing is
    # audited: the append-only store the Progress window depends on is empty.
    status, body = _request(
        app, "PATCH", "/api/projects/P-1/p6/activities/A-1", _progress_patch()
    )
    assert status.startswith("200"), body
    assert body["activity"]["record_revision"] == 2
    history = SQLiteActivityProgressHistoryRepository(connection)
    assert history.list(SCOPE, "A-1") == ()
    connection.close()


def test_partial_progress_wiring_fails_closed_at_the_seam():
    connection = sqlite3.connect(":memory:")
    with pytest.raises(ValueError, match="ACTIVITY_PROGRESS_HISTORY_DEPENDENCIES_INCOMPLETE"):
        build_project_lifecycle_wsgi_app(
            lifecycle_api=_lifecycle_api(frozenset({"project_admin"})),
            snapshot_repository=SQLiteScheduleInputSnapshotRepository(connection),
            calendar_registry_factory=lambda: CalendarResolverRegistry(day_resolvers={}),
            calculation_context_repository=SQLiteCalculationContextRepository(
                connection
            ),
            authorization_policy=default_project_policy(),
            activity_master_repository=SQLiteActivityMasterRepository(connection),
            activity_progress_history_repository=SQLiteActivityProgressHistoryRepository(
                connection
            ),
            # transaction manager deliberately omitted
        )
    connection.close()


def test_wired_composition_records_progress_and_serves_history_over_http():
    connection = sqlite3.connect(":memory:")
    app = _app(connection, wire_progress=True)

    status, body = _request(
        app, "PATCH", "/api/projects/P-1/p6/activities/A-1", _progress_patch()
    )
    assert status.startswith("200"), body
    assert body["activity"]["record_revision"] == 2
    assert body["activity"]["percent_complete"] == 40.0
    assert body["activity"]["remaining_duration"] == 3

    status, history = _request(
        app, "GET", "/api/projects/P-1/p6/activities/A-1/progress-history"
    )
    assert status.startswith("200"), history
    assert history["contract_version"] == "p6-activity-progress-history-api.v1"
    assert [event["to_record_revision"] for event in history["events"]] == [2]
    event = history["events"][0]
    assert event["actor_user_id"] == "u1"
    assert event["from_record_revision"] == 1
    assert {change["field"] for change in event["changes"]} == {
        "actual_start",
        "percent_complete",
        "remaining_duration",
        "status",
        "status_code",
    }
    assert history["percent_complete_trend"] == [
        {
            "to_record_revision": 2,
            "recorded_at": event["recorded_at"],
            "percent_complete": "40.0",
        }
    ]
    # Recording after the finished predecessor is an out-of-sequence fact.
    review = history["out_of_sequence_review"]
    assert review["evaluated_event_id"] == "A-1@2"
    assert review["is_out_of_sequence"] is True
    assert [finding["code"] for finding in review["findings"]] == [
        "FS_START_BEFORE_PREDECESSOR_FINISH"
    ]

    # The persisted event is in the same store operators read, not a response
    # artefact: a fresh repository over the same connection sees it.
    events = SQLiteActivityProgressHistoryRepository(connection).list(SCOPE, "A-1")
    assert len(events) == 1
    assert events[0].from_record_revision == 1
    assert events[0].to_record_revision == 2
    connection.close()


def test_wired_composition_rejects_a_stale_revision_and_keeps_history_immutable():
    connection = sqlite3.connect(":memory:")
    app = _app(connection, wire_progress=True)
    history = SQLiteActivityProgressHistoryRepository(connection)

    status, body = _request(
        app, "PATCH", "/api/projects/P-1/p6/activities/A-1", _progress_patch()
    )
    assert status.startswith("200"), body
    assert len(history.list(SCOPE, "A-1")) == 1

    # A second writer still holding revision 1 must not overwrite revision 2.
    conflict_payload = _progress_patch()
    conflict_payload["percent_complete"] = 90.0
    status, body = _request(
        app, "PATCH", "/api/projects/P-1/p6/activities/A-1", conflict_payload
    )
    assert status.startswith("409"), body
    assert body["code"] == "REVISION_CONFLICT"
    events = history.list(SCOPE, "A-1")
    assert len(events) == 1
    assert "90.0" not in {change.after for change in events[0].changes}
    connection.close()


def test_viewer_can_read_history_but_not_record_progress():
    connection = sqlite3.connect(":memory:")
    app = _app(connection, wire_progress=True, permissions=frozenset({"viewer"}))

    status, history = _request(
        app, "GET", "/api/projects/P-1/p6/activities/A-1/progress-history"
    )
    assert status.startswith("200"), history
    assert history["events"] == []

    status, body = _request(
        app, "PATCH", "/api/projects/P-1/p6/activities/A-1", _progress_patch()
    )
    assert status.startswith("403"), body
    assert body["code"] == "AUTHORIZATION_PERMISSION_DENIED"
    assert SQLiteActivityProgressHistoryRepository(connection).list(SCOPE, "A-1") == ()
    connection.close()


def test_foreign_tenant_cannot_see_or_write_project_progress():
    connection = sqlite3.connect(":memory:")
    app = _app(connection, wire_progress=True, tenant_id="T-2")

    status, body = _request(
        app, "GET", "/api/projects/P-1/p6/activities/A-1/progress-history"
    )
    assert status.startswith("404"), body
    assert body["code"] == "P6_ACTIVITY_PROGRESS_HISTORY_NOT_FOUND"

    status, body = _request(
        app, "PATCH", "/api/projects/P-1/p6/activities/A-1", _progress_patch()
    )
    assert status.startswith("404"), body
    assert body["code"] == "P6_ACTIVITY_MASTER_NOT_FOUND"
    assert SQLiteActivityProgressHistoryRepository(connection).list(SCOPE, "A-1") == ()
    connection.close()
