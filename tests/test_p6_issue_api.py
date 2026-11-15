from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_issue_api import P6_ISSUE_API_VERSION, P6IssueAPI
from construction_pm.p6_issue_repository import P6Issue, SQLiteP6IssueRepository

SCOPE = BackendScope("t1", "p1", 3)
AT = "2026-11-12T08:00:00+00:00"


def api() -> P6IssueAPI:
    return P6IssueAPI(SQLiteP6IssueRepository(sqlite3.connect(":memory:")), default_project_policy())


def planner() -> AuthorizationContext:
    return AuthorizationContext("t1", "p1", "planner-1", frozenset({"planner"}))


def viewer() -> AuthorizationContext:
    return AuthorizationContext("t1", "p1", "viewer-1", frozenset({"viewer"}))


def issue(**overrides) -> P6Issue:
    payload = {
        "scope": SCOPE,
        "issue_id": "ISSUE-API-1",
        "title": "Utility clash at zone B",
        "description": "Storm line clashes with the foundation.",
        "issue_type": "scope",
        "status": "open",
        "priority": "normal",
        "owner": "u-owner",
        "date_identified": "2026-11-05",
    }
    payload.update(overrides)
    return P6Issue(**payload)  # type: ignore[arg-type]


def test_planner_creates_reads_and_lists_issues() -> None:
    service = api()
    created = service.create(issue(), auth_context=planner(), occurred_at=AT)
    assert created["contract_version"] == P6_ISSUE_API_VERSION
    assert created["issue"]["issue_id"] == "ISSUE-API-1"
    assert created["issue"]["record_revision"] == 1
    assert created["scope"]["project_revision"] == 3

    listed = service.list(SCOPE, auth_context=viewer())
    assert [item["issue"]["issue_id"] for item in listed] == ["ISSUE-API-1"]
    assert service.get(SCOPE, "missing", auth_context=viewer()) is None


def test_viewer_cannot_write_or_comment() -> None:
    service = api()
    with pytest.raises(AuthorizationError):
        service.create(issue(), auth_context=viewer(), occurred_at=AT)
    service.create(issue(), auth_context=planner(), occurred_at=AT)
    with pytest.raises(AuthorizationError):
        service.update(issue(title="Changed"), expected_revision=1,
                       auth_context=viewer(), occurred_at=AT)
    with pytest.raises(AuthorizationError):
        service.add_comment(SCOPE, "ISSUE-API-1", comment="note", expected_revision=1,
                            auth_context=viewer(), occurred_at=AT)
    with pytest.raises(AuthorizationError):
        service.delete(SCOPE, "ISSUE-API-1", expected_revision=1,
                       auth_context=viewer(), occurred_at=AT)


def test_cross_scope_is_denied() -> None:
    service = api()
    service.create(issue(), auth_context=planner(), occurred_at=AT)
    other_tenants = AuthorizationContext("t2", "p1", "x", frozenset({"planner"}))
    other_projects = AuthorizationContext("t1", "p2", "x", frozenset({"planner"}))
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.get(SCOPE, "ISSUE-API-1", auth_context=other_tenants)
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.list(SCOPE, auth_context=other_projects)


def test_update_and_history_payloads_keep_identity_and_revision() -> None:
    service = api()
    service.create(issue(), auth_context=planner(), occurred_at=AT)
    updated = service.update(
        issue(priority="high", responsible_manager="m-1"),
        expected_revision=1,
        auth_context=planner(),
        occurred_at="2026-11-12T09:00:00+00:00",
    )
    assert updated["issue"]["record_revision"] == 2
    assert updated["issue"]["priority"] == "high"
    assert updated["issue"]["responsible_manager"] == "m-1"

    history = service.history(SCOPE, "ISSUE-API-1", auth_context=viewer())
    assert [item["event"]["event_type"] for item in history] == ["created", "updated"]
    assert history[-1]["event"]["detail"]["fields"] == ["priority", "responsible_manager"]
    assert history[-1]["event"]["actor_id"] == "planner-1"


class WbsScopedPolicy:
    def __init__(self):
        self.base = default_project_policy()

    def is_allowed(self, context, permission):
        return self.base.is_allowed(context, permission)

    def is_allowed_for_wbs(self, context, permission, wbs_id):
        return wbs_id != "wbs-restricted" and self.base.is_allowed(context, permission)


def test_issue_api_enforces_wbs_scope_for_reads_writes_and_wbs_moves() -> None:
    connection = sqlite3.connect(":memory:")
    repository = SQLiteP6IssueRepository(connection)
    service = P6IssueAPI(repository, WbsScopedPolicy())
    visible = issue(issue_id="VISIBLE-ISSUE", wbs_id="wbs-visible")
    restricted = issue(issue_id="RESTRICTED-ISSUE", wbs_id="wbs-restricted")

    service.create(visible, auth_context=planner(), occurred_at=AT)
    # Seed an existing record through the repository to prove that read and
    # write checks are enforced on records that predate the API request.
    repository.create(restricted, actor_id="seed", occurred_at=AT)

    assert service.get(SCOPE, "RESTRICTED-ISSUE", auth_context=planner()) is None
    assert [item["issue"]["issue_id"] for item in service.list(SCOPE, auth_context=planner())] == [
        "VISIBLE-ISSUE"
    ]
    with pytest.raises(AuthorizationError):
        service.create(restricted, auth_context=planner(), occurred_at=AT)
    with pytest.raises(AuthorizationError):
        service.update(
            restricted, expected_revision=1, auth_context=planner(), occurred_at=AT
        )
    with pytest.raises(AuthorizationError):
        service.update(
            issue(issue_id="VISIBLE-ISSUE", wbs_id="wbs-restricted"),
            expected_revision=1, auth_context=planner(), occurred_at=AT,
        )
    with pytest.raises(AuthorizationError):
        service.delete(
            SCOPE, "RESTRICTED-ISSUE", expected_revision=1,
            auth_context=planner(), occurred_at=AT,
        )
    with pytest.raises(AuthorizationError):
        service.add_comment(
            SCOPE, "RESTRICTED-ISSUE", comment="unauthorized",
            expected_revision=1, auth_context=planner(), occurred_at=AT,
        )
    with pytest.raises(AuthorizationError):
        service.history(SCOPE, "RESTRICTED-ISSUE", auth_context=planner())
    connection.close()
