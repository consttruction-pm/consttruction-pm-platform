from __future__ import annotations

import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_issue_repository import (
    P6Issue,
    P6IssuePersistenceError,
    SQLiteP6IssueRepository,
)

SCOPE = BackendScope("t1", "p1", 3)
AT = "2026-11-12T08:00:00+00:00"


def repo() -> SQLiteP6IssueRepository:
    return SQLiteP6IssueRepository(sqlite3.connect(":memory:"))


def issue(**overrides) -> P6Issue:
    payload = {
        "scope": SCOPE,
        "issue_id": "ISSUE-1",
        "title": "Late structural drawings",
        "description": "Drawing package issued after the planned start.",
        "issue_type": "schedule",
        "status": "open",
        "priority": "high",
        "owner": "u-owner",
        "responsible_manager": "u-manager",
        "date_identified": "2026-11-01",
        "due_date": "2026-11-20",
        "wbs_id": "WBS-1",
        "activity_id": "A100",
        "document_refs": ("DOC-1",),
    }
    payload.update(overrides)
    return P6Issue(**payload)  # type: ignore[arg-type]


def test_issue_roundtrip_and_scope_filters() -> None:
    repository = repo()
    stored = repository.create(issue(), actor_id="u1", occurred_at=AT)
    assert stored.record_revision == 1
    assert stored.created_at == AT
    assert repository.get(SCOPE, "ISSUE-1") == stored
    # Issues are project records, not revision-bound: a newer project revision
    # still reads the same issue instead of hiding it.
    later = repository.get(BackendScope("t1", "p1", 4), "ISSUE-1")
    assert later is not None and later.issue_id == "ISSUE-1"
    assert later.record_revision == 1
    assert repository.get(BackendScope("t2", "p1", 3), "ISSUE-1") is None
    assert repository.get(BackendScope("t1", "p2", 3), "ISSUE-1") is None

    repository.create(
        issue(issue_id="ISSUE-2", title="Missing safety barrier", issue_type="safety",
              priority="critical", owner="u2", date_identified="2026-11-02", due_date=None,
              wbs_id=None, activity_id=None),
        actor_id="u1",
        occurred_at=AT,
    )
    assert [item.issue_id for item in repository.list(SCOPE)] == ["ISSUE-1", "ISSUE-2"]
    assert [item.issue_id for item in repository.list(SCOPE, priority="critical")] == ["ISSUE-2"]
    assert [item.issue_id for item in repository.list(SCOPE, issue_type="safety")] == ["ISSUE-2"]
    assert [item.issue_id for item in repository.list(SCOPE, owner="u-owner")] == ["ISSUE-1"]
    assert [item.issue_id for item in repository.list(SCOPE, search="safety")] == ["ISSUE-2"]
    assert [item.issue_id for item in repository.list(SCOPE, wbs_id="WBS-1")] == ["ISSUE-1"]
    with pytest.raises(P6IssuePersistenceError, match="INVALID_PRIORITY_FILTER"):
        repository.list(SCOPE, priority="urgent")


def test_duplicate_identity_is_rejected() -> None:
    repository = repo()
    repository.create(issue(), actor_id="u1", occurred_at=AT)
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_ALREADY_EXISTS"):
        repository.create(issue(title="Another"), actor_id="u1", occurred_at=AT)


def test_date_and_enum_validation() -> None:
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_DATE_ORDER_INVALID"):
        issue(due_date="2026-10-01").validate()
    with pytest.raises(P6IssuePersistenceError, match="INVALID_PRIORITY"):
        issue(priority="urgent").validate()
    with pytest.raises(P6IssuePersistenceError, match="INVALID_ISSUE_TYPE"):
        issue(issue_type="unknown").validate()
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_RESOLUTION_NOTE_REQUIRED"):
        issue(status="resolved").validate()


def test_revision_guard_and_stale_update() -> None:
    repository = repo()
    repository.create(issue(), actor_id="u1", occurred_at=AT)
    updated = repository.update(
        issue(title="Late structural drawings (revised)", priority="critical"),
        expected_revision=1,
        actor_id="u2",
        occurred_at="2026-11-12T09:00:00+00:00",
    )
    assert updated.record_revision == 2
    assert updated.priority == "critical"
    assert updated.created_at == AT
    assert updated.updated_at == "2026-11-12T09:00:00+00:00"

    with pytest.raises(P6IssuePersistenceError, match="ISSUE_REVISION_CONFLICT"):
        repository.update(issue(title="Lost write"), expected_revision=1, actor_id="u3", occurred_at=AT)


def test_status_transitions_and_resolution_note() -> None:
    repository = repo()
    repository.create(issue(), actor_id="u1", occurred_at=AT)
    closed = repository.update(
        issue(status="closed", resolution_note="Drawings reissued"),
        expected_revision=1,
        actor_id="u1",
        occurred_at="2026-11-12T10:00:00+00:00",
    )
    assert closed.status == "closed"
    # A closed issue is final; silent reopening would hide the closure record.
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_STATUS_TRANSITION_INVALID"):
        repository.update(
            issue(status="open", resolution_note="Drawings reissued"),
            expected_revision=2,
            actor_id="u1",
            occurred_at="2026-11-12T11:00:00+00:00",
        )

    repository.create(
        issue(issue_id="ISSUE-2", title="Second issue"),
        actor_id="u1",
        occurred_at=AT,
    )
    resolved = repository.update(
        issue(issue_id="ISSUE-2", title="Second issue", status="resolved",
              resolution_note="Drawings reissued"),
        expected_revision=1,
        actor_id="u1",
        occurred_at="2026-11-12T10:00:00+00:00",
    )
    assert resolved.record_revision == 2
    assert resolved.status == "resolved"
    reopened = repository.update(
        issue(issue_id="ISSUE-2", title="Second issue", status="open",
              resolution_note="Drawings reissued"),
        expected_revision=2,
        actor_id="u1",
        occurred_at="2026-11-12T11:00:00+00:00",
    )
    assert reopened.status == "open"
    assert reopened.record_revision == 3

    history = repository.history(SCOPE, "ISSUE-2")
    assert [event.event_type for event in history] == [
        "created", "status_changed", "status_changed",
    ]
    assert history[-1].detail["from_status"] == "resolved"
    assert history[-1].detail["to_status"] == "open"


def test_comment_bumps_revision_and_is_audited() -> None:
    repository = repo()
    repository.create(issue(), actor_id="u1", occurred_at=AT)
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_COMMENT_REQUIRED"):
        repository.add_comment(SCOPE, "ISSUE-1", comment="  ", expected_revision=1,
                               actor_id="u1", occurred_at=AT)
    commented = repository.add_comment(
        SCOPE, "ISSUE-1", comment="  Contractor confirmed the new date.  ",
        expected_revision=1, actor_id="u2", occurred_at="2026-11-12T12:00:00+00:00",
    )
    assert commented.record_revision == 2
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_REVISION_CONFLICT"):
        repository.add_comment(SCOPE, "ISSUE-1", comment="stale", expected_revision=1,
                               actor_id="u1", occurred_at=AT)
    history = repository.history(SCOPE, "ISSUE-1")
    assert history[-1].event_type == "commented"
    assert history[-1].detail["comment"] == "Contractor confirmed the new date."
    assert history[-1].actor_id == "u2"


def test_delete_is_revision_guarded_and_keeps_audit_history() -> None:
    repository = repo()
    repository.create(issue(), actor_id="u1", occurred_at=AT)
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_REVISION_CONFLICT"):
        repository.delete(SCOPE, "ISSUE-1", expected_revision=9, actor_id="u1", occurred_at=AT)
    assert repository.delete(SCOPE, "ISSUE-1", expected_revision=1, actor_id="u1", occurred_at=AT)
    assert repository.get(SCOPE, "ISSUE-1") is None
    assert repository.delete(SCOPE, "ISSUE-1", expected_revision=1, actor_id="u1", occurred_at=AT) is False
    history = repository.history(SCOPE, "ISSUE-1")
    assert [event.event_type for event in history] == ["created", "deleted"]


def test_actor_is_required_on_create() -> None:
    repository = repo()
    with pytest.raises(P6IssuePersistenceError, match="ISSUE_ACTOR_REQUIRED"):
        repository.create(issue(), actor_id=" ", occurred_at=AT)
