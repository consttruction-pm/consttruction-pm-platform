from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.document_persistence import (
    DocumentApprovalTransitionError,
    DocumentAuditEvent,
    DocumentIdempotencyReuse,
    DocumentRecord,
    DocumentRevisionConflict,
    SQLiteDocumentStore,
)

NOW = datetime(2026, 11, 12, 8, 15, tzinfo=timezone.utc)


def document(**changes: object) -> DocumentRecord:
    values = {
        "document_id": "DOC-1",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "resource_type": "drawing",
        "title": "Structural drawing revision",
        "status": "draft",
        "storage_ref": "object://documents/DOC-1/rev-1",
        "content_hash": "sha256:" + "a" * 64,
        "linked_entity_refs": ("activity-7",),
    }
    values.update(changes)
    return DocumentRecord(**values)


@pytest.fixture()
def store() -> SQLiteDocumentStore:
    connection = sqlite3.connect(":memory:")
    store = SQLiteDocumentStore(connection)
    store.initialize()
    return store


def test_persist_is_idempotent_and_rejects_reused_key_with_different_payload(store) -> None:
    first = store.persist(document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    replay = store.persist(document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    assert first == replay
    assert first.revision == 1

    with pytest.raises(DocumentIdempotencyReuse, match="DOCUMENT_IDEMPOTENCY_KEY_REUSE"):
        store.persist(
            document(title="Tampered"),
            idempotency_key="idem-1",
            actor_id="user-1",
            occurred_at=NOW,
        )


def test_duplicate_document_id_without_same_idempotency_key_is_rejected(store) -> None:
    store.persist(document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    with pytest.raises(ValueError, match="DOCUMENT_ALREADY_EXISTS"):
        store.persist(document(), idempotency_key="idem-2", actor_id="user-1", occurred_at=NOW)


def test_list_filters_resource_type_status_and_search(store) -> None:
    store.persist(document(), idempotency_key="k-1", actor_id="user-1", occurred_at=NOW)
    store.persist(
        document(document_id="DOC-2", resource_type="rfi", title="RFI 014", status="submitted"),
        idempotency_key="k-2",
        actor_id="user-1",
        occurred_at=NOW,
    )
    store.persist(
        document(document_id="DOC-3", resource_type="drawing", title="Façade detail"),
        idempotency_key="k-3",
        actor_id="user-1",
        occurred_at=NOW,
    )

    assert [item.document.document_id for item in store.list("tenant-1", "project-1")] == [
        "DOC-1",
        "DOC-2",
        "DOC-3",
    ]
    assert [
        item.document.document_id
        for item in store.list("tenant-1", "project-1", resource_type="rfi")
    ] == ["DOC-2"]
    assert [
        item.document.document_id
        for item in store.list("tenant-1", "project-1", status="draft")
    ] == ["DOC-1", "DOC-3"]
    assert [
        item.document.document_id
        for item in store.list("tenant-1", "project-1", search="façade")
    ] == ["DOC-3"]
    assert store.list("tenant-1", "project-1", search="%") == ()
    assert store.list("tenant-1", "project-1", search="_") == ()
    assert store.list("tenant-2", "project-1") == ()
    assert store.list("tenant-1", "project-2") == ()


def test_list_rejects_invalid_filters(store) -> None:
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_RESOURCE_TYPE_FILTER"):
        store.list("tenant-1", "project-1", resource_type="unknown")
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_STATUS_FILTER"):
        store.list("tenant-1", "project-1", status="unknown")
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_SEARCH_FILTER"):
        store.list("tenant-1", "project-1", search="   ")
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_SEARCH_FILTER"):
        store.list("tenant-1", "project-1", search="x" * 201)


def test_search_treats_percent_and_underscore_as_literals(store) -> None:
    store.persist(
        document(document_id="DOC-P", title="Completion 50%"),
        idempotency_key="k-p",
        actor_id="user-1",
        occurred_at=NOW,
    )
    store.persist(
        document(document_id="DOC-Q", title="A_B naming"),
        idempotency_key="k-q",
        actor_id="user-1",
        occurred_at=NOW,
    )

    assert [
        item.document.document_id
        for item in store.list("tenant-1", "project-1", search="50%")
    ] == ["DOC-P"]
    assert [
        item.document.document_id
        for item in store.list("tenant-1", "project-1", search="a_b")
    ] == ["DOC-Q"]


def test_revision_guard_and_append_only_history(store) -> None:
    created = store.persist(document(), idempotency_key="k-1", actor_id="user-1", occurred_at=NOW)
    updated = store.update(
        document(title="Issued for construction"),
        expected_revision=created.revision,
        actor_id="user-2",
        occurred_at=NOW,
    )
    assert updated.revision == 2

    with pytest.raises(DocumentRevisionConflict, match="DOCUMENT_REVISION_CONFLICT"):
        store.update(
            document(title="Stale write"),
            expected_revision=1,
            actor_id="user-3",
            occurred_at=NOW,
        )

    history = store.history("tenant-1", "project-1", "DOC-1")
    assert [(event.revision, event.event_type) for event in history] == [
        (1, "created"),
        (2, "updated"),
    ]
    assert all(isinstance(event, DocumentAuditEvent) for event in history)
    assert history[0].occurred_at == NOW


def test_status_transition_uses_stored_document_and_audits_reason(store) -> None:
    created = store.persist(document(), idempotency_key="k-1", actor_id="user-1", occurred_at=NOW)
    submitted = store.transition_status(
        document(status="submitted", title="tampered"),
        expected_revision=created.revision,
        actor_id="reviewer-1",
        occurred_at=NOW,
        reason="ready for approval",
    )
    assert submitted.document.status == "submitted"
    assert submitted.document.title == "Structural drawing revision"
    assert submitted.revision == 2
    event = store.history("tenant-1", "project-1", "DOC-1")[-1]
    assert event.event_type == "status_transition"
    assert event.actor_id == "reviewer-1"
    assert event.reason == "ready for approval"

    with pytest.raises(
        DocumentApprovalTransitionError,
        match="DOCUMENT_INVALID_STATUS_TRANSITION:submitted->submitted",
    ):
        store.transition_status(
            document(status="submitted"),
            expected_revision=2,
            actor_id="reviewer-1",
            occurred_at=NOW,
        )
    assert store.get("tenant-1", "project-1", "DOC-1").revision == 2


def test_get_missing_document_raises_not_found(store) -> None:
    with pytest.raises(KeyError, match="DOCUMENT_NOT_FOUND"):
        store.get("tenant-1", "project-1", "missing")
    assert store.history("tenant-1", "project-1", "missing") == ()


def test_invalid_metadata_is_rejected_before_write(store) -> None:
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_IDEMPOTENCY_KEY"):
        store.persist(document(), idempotency_key="", actor_id="user-1", occurred_at=NOW)
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_ACTOR"):
        store.persist(document(), idempotency_key="k-1", actor_id="", occurred_at=NOW)
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_AUDIT_TIMESTAMP"):
        store.persist(document(), idempotency_key="k-1", actor_id="user-1", occurred_at=datetime(2026, 11, 12))
    assert store.list("tenant-1", "project-1") == ()


def test_list_is_bounded_to_a_page_and_validates_the_limit(store) -> None:
    for index in range(205):
        store.persist(
            document(document_id=f"DOC-{index:03d}"),
            idempotency_key=f"idem-{index}",
            actor_id="user-1",
            occurred_at=NOW,
        )

    page = store.list("tenant-1", "project-1")
    assert len(page) == 200
    assert [item.document.document_id for item in page] == [
        f"DOC-{index:03d}" for index in range(200)
    ]
    assert len(store.list("tenant-1", "project-1", limit=5)) == 5
    for invalid in (0, -1, 501, True, "10"):
        with pytest.raises(ValueError, match="INVALID_DOCUMENT_PAGE_LIMIT"):
            store.list("tenant-1", "project-1", limit=invalid)


def test_list_all_requires_a_tenant_scope(store) -> None:
    store.persist(document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)

    with pytest.raises(ValueError, match="DOCUMENT_SCOPE_REQUIRED"):
        store.list_all()
    with pytest.raises(ValueError, match="DOCUMENT_SCOPE_REQUIRED"):
        store.list_all(project_id="project-1")
    assert len(store.list_all(tenant_id="tenant-1")) == 1
