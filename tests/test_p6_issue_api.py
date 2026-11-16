from __future__ import annotations

import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
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
        "responsible_obs_id": "OBS-OPERATIONS",
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


def test_issue_access_is_scoped_by_responsible_wbs_obs():
    repository = SQLiteP6IssueRepository(sqlite3.connect(":memory:"))
    base = P6IssueAPI(repository, default_project_policy())
    base.create(issue(wbs_id="W-FOREIGN"), auth_context=planner(), occurred_at=AT)

    class WBSAccess:
        def has_wbs_permission(self, scope, user_id, wbs_id, permission):
            return permission == "issue.view"

    scoped = P6IssueAPI(repository, default_project_policy(), wbs_access_repository=WBSAccess())
    assert scoped.get(SCOPE, "ISSUE-API-1", auth_context=planner())["issue"]["wbs_id"] == "W-FOREIGN"
    assert [item["issue"]["issue_id"] for item in scoped.list(SCOPE, auth_context=planner())] == ["ISSUE-API-1"]
    with pytest.raises(AuthorizationError, match="WBS_OBS_ACCESS_DENIED"):
        scoped.update(
            issue(wbs_id="W-FOREIGN", title="Unauthorized"),
            expected_revision=1, auth_context=planner(), occurred_at=AT,
        )
    with pytest.raises(AuthorizationError, match="ISSUE_RESPONSIBLE_OBS_REQUIRED"):
        scoped.create(
            issue(issue_id="ISSUE-DENIED", wbs_id="W-FOREIGN", responsible_obs_id=None),
            auth_context=planner(), occurred_at=AT,
        )


def test_issue_own_responsible_obs_overrides_project_scope_for_write():
    repository = SQLiteP6IssueRepository(sqlite3.connect(":memory:"))
    base = P6IssueAPI(repository, default_project_policy())
    base.create(
        issue(responsible_obs_id="OBS-QUALITY"),
        auth_context=planner(),
        occurred_at=AT,
    )

    class OBSAccess:
        def has_responsible_obs_permission(self, scope, user_id, obs_id, permission):
            return obs_id == "OBS-QUALITY" and permission == "project.read"

    scoped = P6IssueAPI(repository, default_project_policy(), wbs_access_repository=OBSAccess())
    assert scoped.get(SCOPE, "ISSUE-API-1", auth_context=planner())["issue"]["responsible_obs_id"] == "OBS-QUALITY"
    assert [item["issue"]["issue_id"] for item in scoped.list(SCOPE, auth_context=planner())] == ["ISSUE-API-1"]
    with pytest.raises(AuthorizationError, match="ISSUE_OBS_ACCESS_DENIED"):
        scoped.update(
            issue(responsible_obs_id="OBS-QUALITY", title="Unauthorized edit"),
            expected_revision=1,
            auth_context=planner(),
            occurred_at=AT,
        )
    with pytest.raises(AuthorizationError, match="ISSUE_OBS_ACCESS_DENIED"):
        scoped.add_comment(
            SCOPE, "ISSUE-API-1", comment="Unauthorized", expected_revision=1,
            auth_context=planner(), occurred_at=AT,
        )


def test_issue_responsible_obs_does_not_inherit_project_only_read():
    repository = SQLiteP6IssueRepository(sqlite3.connect(":memory:"))
    base = P6IssueAPI(repository, default_project_policy())
    base.create(issue(responsible_obs_id="OBS-LEGAL"), auth_context=planner(), occurred_at=AT)

    class OBSAccess:
        def has_responsible_obs_permission(self, scope, user_id, obs_id, permission):
            return False

    scoped = P6IssueAPI(repository, default_project_policy(), wbs_access_repository=OBSAccess())
    with pytest.raises(AuthorizationError, match="ISSUE_OBS_ACCESS_DENIED"):
        scoped.get(SCOPE, "ISSUE-API-1", auth_context=planner())
    assert scoped.list(SCOPE, auth_context=planner()) == ()


def test_issue_operations_use_independent_granular_privileges():
    from construction_pm.application.authorization import Permission, RoleBasedAuthorizationPolicy

    policy = RoleBasedAuthorizationPolicy({
        "issue_creator": frozenset({Permission.ISSUE_ADD_EDIT}),
        "issue_editor": frozenset({Permission.ISSUE_EDIT}),
        "issue_reader": frozenset({Permission.ISSUE_VIEW}),
        "issue_deleter": frozenset({Permission.ISSUE_DELETE}),
    })
    service = P6IssueAPI(SQLiteP6IssueRepository(sqlite3.connect(":memory:")), policy)
    def actor(role: str) -> AuthorizationContext:
        return AuthorizationContext("t1", "p1", role, frozenset({role}))

    created = service.create(issue(), auth_context=actor("issue_creator"), occurred_at=AT)
    assert created["issue"]["record_revision"] == 1
    with pytest.raises(AuthorizationError, match="issue.view"):
        service.get(SCOPE, "ISSUE-API-1", auth_context=actor("issue_creator"))
    assert service.get(SCOPE, "ISSUE-API-1", auth_context=actor("issue_reader")) is not None

    updated = service.update(
        issue(title="Granular edit"), expected_revision=1,
        auth_context=actor("issue_editor"), occurred_at=AT,
    )
    assert updated["issue"]["record_revision"] == 2
    with pytest.raises(AuthorizationError, match="issue.delete"):
        service.delete(SCOPE, "ISSUE-API-1", expected_revision=2,
                       auth_context=actor("issue_editor"), occurred_at=AT)
    deleted = service.delete(
        SCOPE, "ISSUE-API-1", expected_revision=2,
        auth_context=actor("issue_deleter"), occurred_at=AT,
    )
    assert deleted["deleted"] is True
