"""Gantt attachments: curtain, text and notebook links."""

from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_gantt_attachment import (
    GanttAttachmentPersistenceError,
    P6GanttAttachmentAPI,
    SQLiteGanttAttachmentRepository,
)

SCOPE = BackendScope("tenant-a", "project-a", 3)


def api() -> P6GanttAttachmentAPI:
    return P6GanttAttachmentAPI(
        SQLiteGanttAttachmentRepository(sqlite3.connect(":memory:")),
        default_project_policy(),
    )


def planner() -> AuthorizationContext:
    return AuthorizationContext("tenant-a", "project-a", "planner-1", frozenset({"planner"}))


def viewer() -> AuthorizationContext:
    return AuthorizationContext("tenant-a", "project-a", "viewer-1", frozenset({"viewer"}))


def test_curtain_text_and_notebook_round_trip() -> None:
    service = api()
    curtain = service.create(
        SCOPE, kind="curtain", label="Winter shutdown", start_date="2027-01-01",
        end_date="2027-01-31", color="#334455", activity_id=None, topic_id=None,
        visible=None, auth_context=planner(),
    )["attachment"]
    text = service.create(
        SCOPE, kind="text", label="Mobilise", start_date="2026-12-01", end_date=None,
        color=None, activity_id="A130", topic_id=None, visible=None, auth_context=planner(),
    )["attachment"]
    topic = service.create(
        SCOPE, kind="notebook", label="Scope agreement", start_date=None, end_date=None,
        color=None, activity_id="A130", topic_id="topic-1", visible=None, auth_context=planner(),
    )["attachment"]
    stored = service.list(SCOPE, auth_context=viewer())["attachments"]
    assert {item["kind"] for item in stored} == {"curtain", "text", "notebook"}
    assert curtain["start_date"] == "2027-01-01" and curtain["color"] == "#334455"
    assert text["activity_id"] == "A130"
    assert topic["topic_id"] == "topic-1"


def test_revision_guard_on_update_and_delete() -> None:
    service = api()
    created = service.create(
        SCOPE, kind="curtain", label="Shutdown", start_date="2027-01-01", end_date="2027-01-31",
        color=None, activity_id=None, topic_id=None, visible=None, auth_context=planner(),
    )["attachment"]
    updated = service.update(
        SCOPE, created["attachment_id"], kind="curtain", label="Shutdown extended",
        start_date="2027-01-01", end_date="2027-02-15", color="#ff8800", activity_id=None,
        topic_id=None, visible=False, expected_record_revision=1, auth_context=planner(),
    )["attachment"]
    assert updated["record_revision"] == 2 and updated["visible"] is False
    with pytest.raises(GanttAttachmentPersistenceError, match="REVISION_CONFLICT"):
        service.update(
            SCOPE, created["attachment_id"], kind="curtain", label="Stale",
            start_date="2027-01-01", end_date="2027-01-31", color=None, activity_id=None,
            topic_id=None, visible=True, expected_record_revision=1, auth_context=planner(),
        )
    with pytest.raises(GanttAttachmentPersistenceError, match="REVISION_CONFLICT"):
        service.delete(SCOPE, created["attachment_id"], expected_record_revision=1, auth_context=planner())
    assert service.delete(SCOPE, created["attachment_id"], expected_record_revision=2, auth_context=planner())["deleted"]


def test_curtain_requires_a_valid_range_and_text_requires_an_activity() -> None:
    service = api()
    with pytest.raises(GanttAttachmentPersistenceError, match="CURTAIN_RANGE_REQUIRED"):
        service.create(SCOPE, kind="curtain", label="x", start_date=None, end_date=None,
                       color=None, activity_id=None, topic_id=None, visible=None, auth_context=planner())
    with pytest.raises(GanttAttachmentPersistenceError, match="INVALID_CURTAIN_RANGE"):
        service.create(SCOPE, kind="curtain", label="x", start_date="2027-02-01", end_date="2027-01-01",
                       color=None, activity_id=None, topic_id=None, visible=None, auth_context=planner())
    with pytest.raises(GanttAttachmentPersistenceError, match="ACTIVITY_REQUIRED"):
        service.create(SCOPE, kind="text", label="x", start_date=None, end_date=None,
                       color=None, activity_id=None, topic_id=None, visible=None, auth_context=planner())
    with pytest.raises(GanttAttachmentPersistenceError, match="TOPIC_REQUIRED"):
        service.create(SCOPE, kind="notebook", label="x", start_date=None, end_date=None,
                       color=None, activity_id="A130", topic_id=None, visible=None, auth_context=planner())
    with pytest.raises(GanttAttachmentPersistenceError, match="INVALID_COLOR"):
        service.create(SCOPE, kind="curtain", label="x", start_date="2027-01-01", end_date="2027-01-02",
                       color="red", activity_id=None, topic_id=None, visible=None, auth_context=planner())


def test_tenant_isolation_and_permissions() -> None:
    service = api()
    service.create(SCOPE, kind="text", label="x", start_date=None, end_date=None,
                   color=None, activity_id="A130", topic_id=None, visible=None, auth_context=planner())
    other = BackendScope("tenant-b", "project-a", 3)
    other_auth = AuthorizationContext("tenant-b", "project-a", "p", frozenset({"planner"}))
    assert service.list(other, auth_context=other_auth)["attachments"] == []
    with pytest.raises(AuthorizationError):
        service.create(SCOPE, kind="text", label="x", start_date=None, end_date=None,
                       color=None, activity_id="A130", topic_id=None, visible=None, auth_context=viewer())
