import os
import uuid
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.document_persistence import (
    DocumentAuthorizationError,
    DocumentIdempotencyReuse,
    DocumentLifecycleService,
    DocumentRecord,
    DocumentRevisionConflict,
    PostgresDocumentStore,
    RoleDocumentLifecycleAuthorizer,
)


def make_document(suffix: str, tenant_id: str = "live-tenant") -> DocumentRecord:
    return DocumentRecord(
        document_id=f"doc-{suffix}",
        tenant_id=tenant_id,
        project_id=f"live-document-project-{suffix}",
        resource_type="contract",
        title="Live PostgreSQL document",
        status="draft",
        storage_ref=f"object://documents/{suffix}",
        content_hash="sha256:" + ("a" * 64),
        linked_entity_refs=("change:1", "claim:1"),
    )


def test_document_live_round_trip_replay_update_conflict_and_audit() -> None:
    suffix = uuid.uuid4().hex
    document = make_document(suffix)
    key = f"document-idem-{suffix}"
    occurred = datetime.now(timezone.utc)

    with psycopg.connect(DSN) as connection:
        store = PostgresDocumentStore(connection)
        store.initialize()
        connection.commit()

        created = store.persist(
            document,
            idempotency_key=key,
            actor_id="live-actor",
            occurred_at=occurred,
        )
        connection.commit()
        assert created.revision == 1
        assert store.get(document.tenant_id, document.project_id, document.document_id) == created

        replay = store.persist(
            document,
            idempotency_key=key,
            actor_id="live-actor",
            occurred_at=occurred,
        )
        assert replay == created

        updated_document = DocumentRecord(
            **{**document.__dict__, "title": "Updated live document"}
        )
        updated = store.update(
            updated_document,
            expected_revision=1,
            actor_id="live-actor",
            occurred_at=occurred,
        )
        connection.commit()
        assert updated.revision == 2
        assert store.get(document.tenant_id, document.project_id, document.document_id) == updated

        with pytest.raises(DocumentRevisionConflict):
            store.update(
                updated_document,
                expected_revision=1,
                actor_id="live-actor",
                occurred_at=occurred,
            )
        connection.rollback()

        with pytest.raises(DocumentIdempotencyReuse):
            store.persist(
                DocumentRecord(**{**document.__dict__, "title": "Different payload"}),
                idempotency_key=key,
                actor_id="live-actor",
                occurred_at=occurred,
            )
        connection.rollback()

        history = store.history(
            document.tenant_id, document.project_id, document.document_id
        )
        assert [event.revision for event in history] == [1, 2]
        assert [event.event_type for event in history] == ["created", "updated"]


def test_document_approval_live_authorization_revision_and_audit() -> None:
    suffix = uuid.uuid4().hex
    document = make_document(suffix)
    occurred = datetime.now(timezone.utc)

    with psycopg.connect(DSN) as connection:
        store = PostgresDocumentStore(connection)
        store.initialize()
        connection.commit()

        store.persist(
            document,
            idempotency_key=f"approval-create-{suffix}",
            actor_id="author",
            occurred_at=occurred,
        )
        connection.commit()

        service = DocumentLifecycleService(
            store,
            RoleDocumentLifecycleAuthorizer({"approver"}),
        )
        submitted = DocumentRecord(**{**document.__dict__, "status": "submitted"})
        service.transition_status(
            submitted,
            expected_revision=1,
            actor_id="author",
            occurred_at=occurred,
            reason="submit for approval",
        )
        connection.commit()

        approved = DocumentRecord(**{**document.__dict__, "status": "approved"})
        with pytest.raises(DocumentAuthorizationError):
            service.transition_status(
                approved,
                expected_revision=2,
                actor_id="author",
                occurred_at=occurred,
                reason="unauthorized approval",
            )
        connection.rollback()

        approved_result = service.transition_status(
            approved,
            expected_revision=2,
            actor_id="approver",
            occurred_at=occurred,
            reason="approved by authorized actor",
        )
        connection.commit()

        assert approved_result.revision == 3
        assert approved_result.document.status == "approved"
        history = store.history(
            document.tenant_id, document.project_id, document.document_id
        )
        assert [event.event_type for event in history] == [
            "created",
            "status_transition",
            "status_transition",
        ]
        assert history[1].reason == "submit for approval"
        assert history[2].reason == "approved by authorized actor"
        assert history[2].actor_id == "approver"


def test_document_content_versions_live_append_isolation_and_idempotency() -> None:
    from construction_pm.document_content_repository import (
        DocumentContentPersistenceError,
        DocumentContentVersion,
        PostgresDocumentContentRepository,
    )
    from construction_pm.document_persistence import DocumentIdempotencyReuse

    suffix = uuid.uuid4().hex
    tenant = f"live-content-tenant-{suffix}"
    project = f"live-content-project-{suffix}"
    document_id = f"doc-{suffix}"
    occurred = datetime.now(timezone.utc)

    def version(
        number: int,
        key: str,
        digest: str,
        *,
        scan_status: str = "unscanned",
        scan_engine: str = "",
        scan_version: str = "",
    ) -> DocumentContentVersion:
        return DocumentContentVersion(
            tenant_id=tenant,
            project_id=project,
            document_id=document_id,
            version=number,
            document_revision=number,
            storage_ref=f"local://{tenant}/{project}/{digest[:8]}",
            content_hash=f"sha256:{digest * 64}",
            content_type="application/pdf",
            byte_size=100 + number,
            original_filename=f"plan-{number}.pdf",
            idempotency_key=key,
            actor_id="live-actor",
            uploaded_at=occurred,
            scan_status=scan_status,
            scan_engine=scan_engine,
            scan_engine_version=scan_version,
        )

    with psycopg.connect(DSN) as connection:
        repository = PostgresDocumentContentRepository(connection)
        repository.initialize()
        connection.commit()

        first = repository.append(version(1, f"content-{suffix}-1", "a"))
        connection.commit()
        assert repository.append(version(1, f"content-{suffix}-1", "a")) == first
        connection.commit()

        with pytest.raises(DocumentIdempotencyReuse):
            repository.append(version(2, f"content-{suffix}-1", "b"))
        connection.rollback()

        with pytest.raises(DocumentContentPersistenceError):
            repository.append(version(3, f"content-{suffix}-3", "c"))
        connection.rollback()

        second = repository.append(version(2, f"content-{suffix}-2", "b"))
        connection.commit()
        assert repository.latest(tenant, project, document_id) == second
        # Legacy rows written without scan metadata remain readable and explicit.
        assert first.scan_status == "unscanned"
        assert first.scan_engine == ""
        assert repository.get(tenant, project, document_id, 1).as_dict()["scan"] == {
            "status": "unscanned",
            "engine": "",
            "engine_version": "",
            "detail": "",
        }

        scanned = repository.append(
            version(
                3,
                f"content-{suffix}-3",
                "c",
                scan_status="clean",
                scan_engine="live-engine",
                scan_version="9.1",
            )
        )
        connection.commit()
        assert scanned.version == 3
        assert scanned.as_dict()["scan"] == {
            "status": "clean",
            "engine": "live-engine",
            "engine_version": "9.1",
            "detail": "",
        }
        assert [item.version for item in repository.list(tenant, project, document_id)] == [1, 2, 3]
        assert repository.get(tenant, project, document_id, 1) == first
        assert repository.get(tenant, project, document_id, 9) is None
        assert repository.latest(tenant, project, "other-document") is None
        assert repository.latest("other-tenant", project, document_id) is None
