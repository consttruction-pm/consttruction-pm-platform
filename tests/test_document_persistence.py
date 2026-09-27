from __future__ import annotations

from datetime import datetime, timezone

import pytest

from construction_pm.document_persistence import (
    DocumentApprovalTransitionError,
    DocumentIdempotencyReuse,
    DocumentRecord,
    DocumentRevisionConflict,
    PostgresDocumentStore,
)


class FakeResult:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.documents = {}
        self.audit = []

    def execute(self, sql, params=()):
        if sql.startswith("CREATE TABLE"):
            return FakeResult()
        if sql.startswith("INSERT INTO project_documents"):
            key = params[:3]
            self.documents[key] = {
                "idempotency_key": params[3],
                "fingerprint": params[4],
                "revision": params[5],
                "json": params[6],
            }
            return FakeResult()
        if sql.startswith("INSERT INTO project_document_audit"):
            self.audit.append(params)
            return FakeResult()
        if sql.startswith("SELECT document_id, fingerprint, revision"):
            tenant, project, idem = params
            for (t, p, d), row in self.documents.items():
                if (t, p) == (tenant, project) and row["idempotency_key"] == idem:
                    return FakeResult([(d, row["fingerprint"], row["revision"])])
            return FakeResult()
        if sql.startswith("SELECT document_json, revision"):
            key = params
            row = self.documents.get(key)
            return FakeResult([] if row is None else [(row["json"], row["revision"])])
        if sql.startswith("UPDATE project_documents"):
            revision, payload, tenant, project, document_id = params
            self.documents[(tenant, project, document_id)]["revision"] = revision
            self.documents[(tenant, project, document_id)]["json"] = payload
            return FakeResult()
        if sql.startswith("SELECT revision, event_type, actor_id, occurred_at"):
            tenant, project, document_id = params
            rows = [
                (r[3], r[4], r[5], r[6])
                for r in self.audit
                if r[0] == tenant and r[1] == project and r[2] == document_id
            ]
            return FakeResult(rows)
        raise AssertionError(f"unexpected SQL: {sql}")


def make_document(**changes):
    values = {
        "document_id": "doc-1",
        "tenant_id": "tenant-1",
        "project_id": "project-1",
        "resource_type": "drawing",
        "title": "Structural drawing",
        "status": "draft",
        "storage_ref": "object://documents/doc-1/rev-1",
        "content_hash": "sha256:" + "a" * 64,
        "linked_entity_refs": ("activity-7", "cost-3"),
    }
    values.update(changes)
    return DocumentRecord(**values)


NOW = datetime(2026, 9, 27, 5, 30, tzinfo=timezone.utc)


def test_document_record_rejects_invalid_type_and_hash():
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_RESOURCE_TYPE"):
        make_document(resource_type="unknown").validate()
    with pytest.raises(ValueError, match="INVALID_DOCUMENT_CONTENT_HASH"):
        make_document(content_hash="md5:bad").validate()


def test_persist_replays_same_idempotency_key():
    connection = FakeConnection()
    store = PostgresDocumentStore(connection)
    first = store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    replay = store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    assert first == replay
    assert len(connection.audit) == 1


def test_idempotency_reuse_is_rejected():
    connection = FakeConnection()
    store = PostgresDocumentStore(connection)
    store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    with pytest.raises(DocumentIdempotencyReuse, match="DOCUMENT_IDEMPOTENCY_KEY_REUSE"):
        store.persist(make_document(title="Tampered"), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)


def test_stale_revision_is_rejected_and_history_is_append_only():
    connection = FakeConnection()
    store = PostgresDocumentStore(connection)
    created = store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    updated = store.update(make_document(status="submitted"), expected_revision=created.revision, actor_id="user-2", occurred_at=NOW)
    assert updated.revision == 2
    with pytest.raises(DocumentRevisionConflict, match="DOCUMENT_REVISION_CONFLICT"):
        store.update(make_document(status="approved"), expected_revision=1, actor_id="user-3", occurred_at=NOW)
    assert [event.revision for event in store.history("tenant-1", "project-1", "doc-1")] == [1, 2]


def test_revision_safe_ceiling_is_enforced():
    connection = FakeConnection()
    store = PostgresDocumentStore(connection)
    store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)
    connection.documents[("tenant-1", "project-1", "doc-1")]["revision"] = 9_007_199_254_740_991
    with pytest.raises(ValueError, match="DOCUMENT_REVISION_EXHAUSTED"):
        store.update(make_document(status="submitted"), expected_revision=9_007_199_254_740_991, actor_id="user-2", occurred_at=NOW)


def test_document_approval_lifecycle_enforces_allowed_transitions_and_audits_actor():
    connection = FakeConnection()
    store = PostgresDocumentStore(connection)
    created = store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)

    submitted = store.transition_status(
        make_document(status="submitted"),
        expected_revision=created.revision,
        actor_id="reviewer-1",
        occurred_at=NOW,
        reason="ready for review",
    )
    assert submitted.document.status == "submitted"
    assert submitted.revision == 2

    approved = store.transition_status(
        make_document(status="approved"),
        expected_revision=submitted.revision,
        actor_id="approver-1",
        occurred_at=NOW,
        reason="accepted",
    )
    assert approved.document.status == "approved"
    assert approved.revision == 3
    assert [event.event_type for event in store.history("tenant-1", "project-1", "doc-1")] == [
        "created",
        "status:draft->submitted:ready for review",
        "status:submitted->approved:accepted",
    ]


def test_document_approval_rejects_invalid_transition_and_does_not_mutate():
    connection = FakeConnection()
    store = PostgresDocumentStore(connection)
    created = store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)

    with pytest.raises(
        DocumentApprovalTransitionError,
        match="DOCUMENT_INVALID_STATUS_TRANSITION:draft->approved",
    ):
        store.transition_status(
            make_document(status="approved"),
            expected_revision=created.revision,
            actor_id="approver-1",
            occurred_at=NOW,
        )

    current = store.get("tenant-1", "project-1", "doc-1")
    assert current.document.status == "draft"
    assert current.revision == 1
    assert len(store.history("tenant-1", "project-1", "doc-1")) == 1


def test_document_approval_uses_current_document_payload_not_caller_mutations():
    connection = FakeConnection()
    store = PostgresDocumentStore(connection)
    created = store.persist(make_document(), idempotency_key="idem-1", actor_id="user-1", occurred_at=NOW)

    store.transition_status(
        make_document(status="submitted", title="tampered title", storage_ref="object://tampered"),
        expected_revision=created.revision,
        actor_id="reviewer-1",
        occurred_at=NOW,
    )
    current = store.get("tenant-1", "project-1", "doc-1")
    assert current.document.status == "submitted"
    assert current.document.title == "Structural drawing"
    assert current.document.storage_ref == "object://documents/doc-1/rev-1"
