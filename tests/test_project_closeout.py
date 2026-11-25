"""Project closeout and reopening: revision guards, gate and audit."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.project_closeout import (
    CLOSEOUT_CONTRACT_VERSION,
    CloseoutEvent,
    ProjectCloseout,
    ProjectCloseoutAPI,
    ProjectCloseoutAuthorizationError,
    ProjectCloseoutBlocked,
    ProjectCloseoutError,
    ProjectCloseoutRevisionConflict,
    ProjectCloseoutService,
)

TENANT = "tenant-closeout"
PROJECT = "project-closeout"
ADMIN = "admin-closeout"
PLANNER = "planner-closeout"
VIEWER = "viewer-closeout"
NOW = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)


class _Transactions:
    def transaction(self):
        return nullcontext()


def _policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(
        {
            "project_admin": frozenset(
                {Permission.PROJECT_READ, Permission.PROJECT_ADMIN}
            ),
            "planner": frozenset(
                {Permission.PROJECT_READ, Permission.PROJECT_WRITE}
            ),
            "viewer": frozenset({Permission.PROJECT_READ}),
        }
    )


def _context(role: str, user_id: str = ADMIN) -> AuthorizationContext:
    return AuthorizationContext(TENANT, PROJECT, user_id, frozenset({role}))


def _issue(status: str):
    return SimpleNamespace(status=status)


class _IssueRepository:
    def __init__(self, statuses=()):
        self.statuses = list(statuses)
        self.scopes = []

    def list(self, scope):
        self.scopes.append((scope.tenant_id, scope.project_id, scope.project_revision))
        return tuple(_issue(status) for status in self.statuses)


class _Store:
    """In-memory mirror of the PostgreSQL store's guarded writes."""

    def __init__(self):
        self.row: ProjectCloseout | None = None
        self.events: list[CloseoutEvent] = []
        self.transitions = 0

    def get(self, tenant_id, project_id):
        return self.row

    def history(self, tenant_id, project_id):
        return tuple(self.events)

    def transition(self, *, expected_revision, state, event):
        self.transitions += 1
        current = 0 if self.row is None else self.row.record_revision
        if current != expected_revision:
            raise ProjectCloseoutRevisionConflict("CLOSEOUT_REVISION_CONFLICT")
        self.row = state
        self.events.append(event)
        return state


def _service(issues=None):
    store = _Store()
    repository = _IssueRepository(issues or ())
    service = ProjectCloseoutService(store, repository, _policy(), _Transactions())
    return service, store, repository


def _close(service, *, expected_revision=0, note="", context=None, actor=ADMIN):
    return service.close(
        tenant_id=TENANT,
        project_id=PROJECT,
        project_revision=3,
        expected_revision=expected_revision,
        note=note,
        context=context or _context("project_admin"),
        actor_id=actor,
        occurred_at=NOW,
    )


def _reopen(service, *, expected_revision, note="", context=None, actor=ADMIN):
    return service.reopen(
        tenant_id=TENANT,
        project_id=PROJECT,
        project_revision=3,
        expected_revision=expected_revision,
        note=note,
        context=context or _context("project_admin"),
        actor_id=actor,
        occurred_at=NOW,
    )


def test_read_defaults_to_open_and_requires_project_scope():
    service, store, _repository = _service()

    state = service.read(tenant_id=TENANT, project_id=PROJECT, context=_context("viewer", VIEWER))
    assert state.state == "open"
    assert state.record_revision == 0
    assert store.transitions == 0

    with pytest.raises(ProjectCloseoutAuthorizationError) as cross_tenant:
        service.read(
            tenant_id="other-tenant", project_id=PROJECT, context=_context("viewer", VIEWER)
        )
    assert str(cross_tenant.value) == "CLOSEOUT_CROSS_SCOPE_ACCESS"

    with pytest.raises(ProjectCloseoutAuthorizationError) as denied:
        service.read(tenant_id=TENANT, project_id=PROJECT, context=_context("nobody", VIEWER))
    assert str(denied.value) == "CLOSEOUT_PERMISSION_DENIED"


def test_close_is_blocked_by_open_issues_and_writes_nothing():
    service, store, repository = _service(("open", "in_progress", "resolved", "closed"))

    with pytest.raises(ProjectCloseoutBlocked) as blocked:
        _close(service)
    assert str(blocked.value) == "CLOSEOUT_OPEN_ISSUES:2"
    assert store.transitions == 0
    assert store.row is None and store.events == []
    assert repository.scopes == [(TENANT, PROJECT, 3)]


def test_close_writes_one_revision_and_one_event():
    service, store, _repository = _service(("resolved",))

    closed = _close(service, note="  all issues resolved  ")
    assert closed.state == "closed"
    assert closed.record_revision == 1
    assert closed.closed_by == ADMIN
    assert closed.closed_at == NOW
    assert closed.note == "all issues resolved"
    assert store.transitions == 1
    assert [(item.event_id, item.action, item.record_revision) for item in store.events] == [
        ("closed-1", "closed", 1)
    ]

    history = service.history(
        tenant_id=TENANT, project_id=PROJECT, context=_context("viewer", VIEWER)
    )
    assert history == tuple(store.events)


def test_repeated_close_is_an_idempotent_no_op():
    service, store, _repository = _service()

    _close(service)
    again = _close(service, expected_revision=9)

    assert again.record_revision == 1
    assert store.transitions == 1
    assert len(store.events) == 1


def test_stale_revision_is_a_conflict_and_changes_nothing():
    service, store, _repository = _service()
    _close(service)

    with pytest.raises(ProjectCloseoutRevisionConflict) as conflict:
        _reopen(service, expected_revision=0)
    assert str(conflict.value) == "CLOSEOUT_REVISION_CONFLICT"
    assert store.row is not None and store.row.state == "closed"
    assert len(store.events) == 1


def test_reopen_moves_to_the_next_revision_and_records_open_issues():
    service, store, repository = _service()
    _close(service)

    repository.statuses = ["open"]
    reopened = _reopen(service, expected_revision=1, note="punch list")
    assert reopened.state == "open"
    assert reopened.record_revision == 2
    assert reopened.closed_at is None
    assert reopened.closed_by == ""
    assert reopened.open_issue_count == 1
    assert [item.action for item in store.events] == ["closed", "reopened"]

    # Reopening an open project is idempotent even with a stale revision.
    again = _reopen(service, expected_revision=0)
    assert again.record_revision == 2
    assert store.transitions == 2


def test_write_requires_project_admin_and_matching_actor():
    service, store, _repository = _service()

    with pytest.raises(ProjectCloseoutAuthorizationError) as denied:
        _close(service, context=_context("planner", PLANNER), actor=PLANNER)
    assert str(denied.value) == "CLOSEOUT_PERMISSION_DENIED"

    with pytest.raises(ProjectCloseoutAuthorizationError) as mismatch:
        _close(service, context=_context("project_admin"), actor=PLANNER)
    assert str(mismatch.value) == "CLOSEOUT_ACTOR_MISMATCH"

    assert store.transitions == 0


def test_note_is_trimmed_and_bounded():
    service, _store, _repository = _service()

    closed = _close(service, note=" x" * 3000)
    assert len(closed.note) == 2000
    assert closed.note.startswith("x x x")


def test_naive_timestamps_are_rejected():
    service, _store, _repository = _service()

    with pytest.raises(ProjectCloseoutError) as invalid:
        service.close(
            tenant_id=TENANT,
            project_id=PROJECT,
            project_revision=3,
            expected_revision=0,
            note="",
            context=_context("project_admin"),
            actor_id=ADMIN,
            occurred_at=datetime(2026, 11, 25, 10, 0),
        )
    assert str(invalid.value) == "CLOSEOUT_OCCURRED_AT_INVALID"


def test_error_dto_maps_categories_with_non_empty_messages():
    blocked = ProjectCloseoutService.error_dto(
        ProjectCloseoutBlocked("CLOSEOUT_OPEN_ISSUES:3")
    )
    assert blocked.category.value == "conflict"
    assert blocked.code == "CLOSEOUT_OPEN_ISSUES:3"

    conflict = ProjectCloseoutService.error_dto(
        ProjectCloseoutRevisionConflict("CLOSEOUT_REVISION_CONFLICT")
    )
    assert conflict.category.value == "conflict"
    assert conflict.code == "CLOSEOUT_REVISION_CONFLICT"

    denied = ProjectCloseoutService.error_dto(
        ProjectCloseoutAuthorizationError("CLOSEOUT_PERMISSION_DENIED")
    )
    assert denied.category.value == "authorization"

    invalid = ProjectCloseoutService.error_dto(ValueError("CLOSEOUT_NOTE_INVALID"))
    assert invalid.category.value == "validation"

    internal = ProjectCloseoutService.error_dto(RuntimeError(""))
    assert internal.category.value == "validation"
    assert internal.code == "CLOSEOUT_INTERNAL_ERROR"
    assert internal.message

    for error in (blocked, conflict, denied, invalid, internal):
        error.validate()


def test_api_returns_contract_payloads_and_bounded_errors():
    service, _store, _repository = _service(("open",))
    api = ProjectCloseoutAPI(service)
    context = _context("project_admin")

    blocked = api.close(
        tenant_id=TENANT,
        project_id=PROJECT,
        project_revision=3,
        expected_revision=0,
        note="",
        context=context,
        actor_id=ADMIN,
        occurred_at=NOW,
    )
    assert blocked["contract_version"] == CLOSEOUT_CONTRACT_VERSION
    assert blocked["category"] == "conflict"
    assert blocked["code"] == "CLOSEOUT_OPEN_ISSUES:1"
    assert blocked["message"]

    denied = api.read(
        tenant_id=TENANT, project_id=PROJECT, context=_context("nobody", VIEWER)
    )
    assert denied["category"] == "authorization"

    state = api.read(
        tenant_id=TENANT, project_id=PROJECT, context=_context("viewer", VIEWER)
    )
    assert state["contract_version"] == CLOSEOUT_CONTRACT_VERSION
    assert state["closeout"]["state"] == "open"
    history = api.history(
        tenant_id=TENANT, project_id=PROJECT, context=_context("viewer", VIEWER)
    )
    assert history["events"] == []
