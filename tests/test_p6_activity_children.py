"""Activity Codes and Notebook: authorisation, persistence and revision guard."""

from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_children import (
    ActivityChildPersistenceError,
    P6ActivityChildrenAPI,
    SQLiteActivityChildrenRepository,
    sanitize_notebook_html,
)

SCOPE = BackendScope("tenant-a", "project-a", 1)


def api() -> P6ActivityChildrenAPI:
    return P6ActivityChildrenAPI(
        SQLiteActivityChildrenRepository(sqlite3.connect(":memory:")),
        default_project_policy(),
    )


def member(project: str = "project-a", tenant: str = "tenant-a") -> AuthorizationContext:
    return AuthorizationContext(tenant, project, "planner-1", frozenset({"planner"}))


def viewer() -> AuthorizationContext:
    return AuthorizationContext("tenant-a", "project-a", "viewer-1", frozenset({"viewer"}))


def test_code_assignment_is_persisted_and_replaced_by_type() -> None:
    service = api()
    first = service.assign_code(
        SCOPE, "A130", code_type="AREA", code_value="ZONE-1", description="North", auth_context=member()
    )["code"]
    assert first["record_revision"] == 1
    changed = service.assign_code(
        SCOPE, "A130", code_type="AREA", code_value="ZONE-2", description="South", auth_context=member()
    )["code"]
    assert changed["assignment_id"] == first["assignment_id"]
    assert changed["record_revision"] == 2
    codes = service.list_codes(SCOPE, "A130", auth_context=viewer())["codes"]
    assert [(item["code_type"], item["code_value"]) for item in codes] == [("AREA", "ZONE-2")]


def test_code_lists_are_tenant_project_and_activity_isolated() -> None:
    service = api()
    service.assign_code(SCOPE, "A130", code_type="AREA", code_value="ZONE-1", description=None, auth_context=member())
    assert service.list_codes(BackendScope("tenant-b", "project-a", 1), "A130", auth_context=member("project-a", "tenant-b"))["codes"] == []
    assert service.list_codes(BackendScope("tenant-a", "project-b", 1), "A130", auth_context=member("project-b"))["codes"] == []
    assert service.list_codes(SCOPE, "A140", auth_context=viewer())["codes"] == []


def test_remove_code_requires_the_matching_assignment() -> None:
    service = api()
    code = service.assign_code(
        SCOPE, "A130", code_type="AREA", code_value="ZONE-1", description=None, auth_context=member()
    )["code"]
    with pytest.raises(ActivityChildPersistenceError, match="ACTIVITY_CODE_NOT_FOUND"):
        service.remove_code(SCOPE, "A140", code["assignment_id"], auth_context=member())
    assert service.remove_code(SCOPE, "A130", code["assignment_id"], auth_context=member())["deleted"] is True
    assert service.list_codes(SCOPE, "A130", auth_context=viewer())["codes"] == []


def test_viewer_cannot_write_codes_or_notebook() -> None:
    service = api()
    with pytest.raises(AuthorizationError):
        service.assign_code(SCOPE, "A130", code_type="AREA", code_value="Z", description=None, auth_context=viewer())
    with pytest.raises(AuthorizationError):
        service.add_topic(SCOPE, "A130", topic_name="T", description="d", auth_context=viewer())


def test_cross_scope_access_is_rejected() -> None:
    service = api()
    with pytest.raises(AuthorizationError):
        service.list_codes(BackendScope("tenant-b", "project-a", 1), "A130", auth_context=member())


def test_notebook_add_update_delete_round_trip_with_revision_guard() -> None:
    service = api()
    topic = service.add_topic(
        SCOPE, "A130", topic_name="Kickoff", description="<p>Discuss <b>scope</b></p>", auth_context=member()
    )["topic"]
    assert topic["description"] == "<p>Discuss <b>scope</b></p>"
    updated = service.update_topic(
        SCOPE,
        "A130",
        topic["topic_id"],
        topic_name="Kickoff meeting",
        description="<p>Scope agreed</p>",
        expected_record_revision=1,
        auth_context=member(),
    )["topic"]
    assert updated["record_revision"] == 2
    with pytest.raises(ActivityChildPersistenceError, match="REVISION_CONFLICT"):
        service.update_topic(
            SCOPE,
            "A130",
            topic["topic_id"],
            topic_name="Stale",
            description="x",
            expected_record_revision=1,
            auth_context=member(),
        )
    with pytest.raises(ActivityChildPersistenceError, match="REVISION_CONFLICT"):
        service.delete_topic(SCOPE, "A130", topic["topic_id"], expected_record_revision=1, auth_context=member())
    assert service.delete_topic(SCOPE, "A130", topic["topic_id"], expected_record_revision=2, auth_context=member())["deleted"] is True
    assert service.list_notebook(SCOPE, "A130", auth_context=viewer())["topics"] == []


def test_notebook_html_is_sanitised_to_the_allow_list() -> None:
    assert sanitize_notebook_html("<p onclick='x()'>Hi<script>alert(1)</script><b>there</b></p>") == "<p>Hialert(1)<b>there</b></p>"
    assert sanitize_notebook_html("<a href='https://example.com'>link</a>") == "link"


def test_notebook_topics_are_ordered_by_sequence() -> None:
    service = api()
    service.add_topic(SCOPE, "A130", topic_name="First", description="1", auth_context=member())
    service.add_topic(SCOPE, "A130", topic_name="Second", description="2", auth_context=member())
    topics = service.list_notebook(SCOPE, "A130", auth_context=viewer())["topics"]
    assert [item["topic_name"] for item in topics] == ["First", "Second"]
    assert [item["sequence"] for item in topics] == [1, 2]
