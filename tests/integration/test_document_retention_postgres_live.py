import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip(
        "CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True
    )

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.document_content_repository import (
    DocumentContentVersion,
    PostgresDocumentContentRepository,
)
from construction_pm.document_persistence import PostgresDocumentStore
from construction_pm.document_retention import (
    DocumentContentAlreadyDisposed,
    DocumentDisposition,
    DocumentRetentionPolicy,
    DocumentRetentionRevisionConflict,
    DocumentRetentionService,
    PostgresDocumentRetentionStore,
)


def _policy(suffix: str, *, retain_days: int = 30, legal_hold: bool = False):
    now = datetime.now(timezone.utc)
    return DocumentRetentionPolicy(
        tenant_id=f"retention-tenant-{suffix}",
        project_id=f"retention-project-{suffix}",
        document_id=f"document-{suffix}",
        retain_days=retain_days,
        legal_hold=legal_hold,
        reason="live retention policy",
        updated_by="live-actor",
        updated_at=now,
    )


def test_retention_policy_and_disposition_live_parity() -> None:
    suffix = uuid.uuid4().hex
    with psycopg.connect(DSN) as connection:
        store = PostgresDocumentRetentionStore(connection)
        store.initialize()
        connection.commit()

        created = store.set_policy(_policy(suffix), expected_revision=0)
        connection.commit()
        assert created.revision == 1
        assert created.retain_days == 30
        assert created.legal_hold is False

        with pytest.raises(DocumentRetentionRevisionConflict):
            store.set_policy(_policy(suffix), expected_revision=0)

        updated = store.set_policy(
            _policy(suffix, retain_days=90, legal_hold=True), expected_revision=1
        )
        connection.commit()
        assert updated.revision == 2
        assert updated.retain_days == 90
        assert updated.legal_hold is True
        assert store.get_policy(
            created.tenant_id, created.project_id, created.document_id
        ) == updated

        disposition = DocumentDisposition(
            tenant_id=created.tenant_id,
            project_id=created.project_id,
            document_id=created.document_id,
            version=1,
            content_hash="sha256:" + "a" * 64,
            reason="live disposition",
            actor_id="live-actor",
            disposed_at=datetime.now(timezone.utc),
        )
        recorded = store.record_disposition(disposition)
        connection.commit()
        assert recorded == disposition
        assert store.get_disposition(
            disposition.tenant_id,
            disposition.project_id,
            disposition.document_id,
            1,
        ) == disposition
        assert store.list_dispositions(
            disposition.tenant_id, disposition.project_id, disposition.document_id
        ) == (disposition,)

        with pytest.raises(DocumentContentAlreadyDisposed):
            store.record_disposition(disposition)


class _RecordingStorage:
    """Records object deletions so the test can prove bytes survived."""

    def __init__(self, storage_ref: str) -> None:
        self.storage_ref = storage_ref
        self.deleted: list[str] = []

    def delete(self, storage_ref: str, *, tenant_id: str, project_id: str) -> None:
        assert storage_ref == self.storage_ref
        assert tenant_id and project_id
        self.deleted.append(storage_ref)


def test_dispose_keeps_bytes_shared_with_a_live_sibling_live() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"retention-tenant-{suffix}"
    project_id = f"retention-project-{suffix}"
    now = datetime.now(timezone.utc)
    uploaded_at = now.replace(microsecond=0)
    storage_ref = f"local:v1/{suffix[:8]}/{suffix[8:16]}/ab/{'a' * 64}.txt"
    content_hash = "sha256:" + "a" * 64
    with psycopg.connect(DSN) as connection:
        retention_store = PostgresDocumentRetentionStore(connection)
        retention_store.initialize()
        content_repository = PostgresDocumentContentRepository(connection)
        content_repository.initialize()
        document_store = PostgresDocumentStore(connection)
        document_store.initialize()
        connection.commit()

        for document_id in ("DOC-A", "DOC-B"):
            content_repository.append(
                DocumentContentVersion(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    document_id=document_id,
                    version=1,
                    document_revision=2,
                    storage_ref=storage_ref,
                    content_hash=content_hash,
                    content_type="text/plain",
                    byte_size=17,
                    original_filename="notes.txt",
                    idempotency_key=f"upload-{document_id}",
                    actor_id="live-actor",
                    uploaded_at=uploaded_at - timedelta(hours=1),
                )
            )
            retention_store.set_policy(
                DocumentRetentionPolicy(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    document_id=document_id,
                    retain_days=0,
                    legal_hold=False,
                    reason="live retention policy",
                    updated_by="live-actor",
                    updated_at=now,
                ),
                expected_revision=0,
            )
        connection.commit()

        storage = _RecordingStorage(storage_ref)
        service = DocumentRetentionService(
            retention_store,
            content_repository,
            document_store,
            storage,
            default_project_policy(),
        )
        context = AuthorizationContext(
            tenant_id, project_id, "live-actor", frozenset({"project_admin"})
        )

        first = service.dispose(
            tenant_id=tenant_id,
            project_id=project_id,
            document_id="DOC-A",
            version=1,
            confirm="DOC-A:1",
            reason="expired",
            context=context,
            actor_id="live-actor",
            occurred_at=now,
        )
        connection.commit()
        assert first.version == 1
        assert storage.deleted == []
        assert retention_store.get_disposition(tenant_id, project_id, "DOC-A", 1) is not None

        service.dispose(
            tenant_id=tenant_id,
            project_id=project_id,
            document_id="DOC-B",
            version=1,
            confirm="DOC-B:1",
            reason="expired",
            context=context,
            actor_id="live-actor",
            occurred_at=now,
        )
        connection.commit()
        assert storage.deleted == [storage_ref]

        with pytest.raises(DocumentContentAlreadyDisposed):
            service.dispose(
                tenant_id=tenant_id,
                project_id=project_id,
                document_id="DOC-A",
                version=1,
                confirm="DOC-A:1",
                reason="expired",
                context=context,
                actor_id="live-actor",
                occurred_at=now,
            )

        for table in (
            "project_document_content",
            "project_document_retention",
            "project_document_disposition",
        ):
            connection.execute(
                f"DELETE FROM {table} WHERE tenant_id=%s AND project_id=%s",
                (tenant_id, project_id),
            )
        connection.commit()
