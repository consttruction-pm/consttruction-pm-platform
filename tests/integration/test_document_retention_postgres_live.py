import os
import uuid
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip(
        "CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True
    )

from construction_pm.document_retention import (
    DocumentContentAlreadyDisposed,
    DocumentDisposition,
    DocumentRetentionPolicy,
    DocumentRetentionRevisionConflict,
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
