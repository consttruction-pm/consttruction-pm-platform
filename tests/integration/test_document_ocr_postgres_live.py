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

from construction_pm.document_ocr import (
    DocumentOcrJob,
    DocumentOcrNotRetryable,
    OcrExtraction,
    PostgresDocumentOcrRepository,
)


def _job(suffix: str, version: int = 1, *, max_attempts: int = 3) -> DocumentOcrJob:
    now = datetime.now(timezone.utc)
    digest = f"{version:064x}"
    return DocumentOcrJob(
        tenant_id=f"ocr-tenant-{suffix}",
        project_id=f"ocr-project-{suffix}",
        document_id=f"doc-{suffix}",
        version=version,
        storage_ref=f"local:v1/{suffix}/{version}",
        content_hash=f"sha256:{digest}",
        content_type="text/plain",
        byte_size=32,
        original_filename="notes.txt",
        requested_by="live-actor",
        requested_at=now,
        max_attempts=max_attempts,
        next_attempt_at=now,
    )


def test_ocr_queue_live_claim_complete_and_retry_parity() -> None:
    suffix = uuid.uuid4().hex
    with psycopg.connect(DSN) as connection:
        repository = PostgresDocumentOcrRepository(connection)
        repository.initialize()
        connection.commit()
        # claim_due() is intentionally cross-tenant, so purge rows left behind by
        # earlier runs of this test before asserting on the claimed batch size.
        connection.execute(
            "DELETE FROM project_document_ocr WHERE tenant_id LIKE 'ocr-tenant-%'"
        )
        connection.commit()

        job = _job(suffix)
        created = repository.request(job)
        connection.commit()
        assert created.status == "pending"
        assert repository.request(_job(suffix)) == created

        claimed = repository.claim_due(datetime.now(timezone.utc), "live-worker", 5)
        assert len(claimed) == 1
        assert claimed[0].claim_token
        assert claimed[0].claimed_by == "live-worker"
        now = datetime.now(timezone.utc)
        assert repository.claim_due(now, "other-worker", 5) == ()

        completed = repository.complete(
            claimed[0], OcrExtraction("live text", "live-engine", "2"), now
        )
        connection.commit()
        assert completed.status == "succeeded"
        assert completed.text == "live text"
        assert completed.char_count == len("live text")
        assert repository.get(job.tenant_id, job.project_id, job.document_id, 1) == completed

        with pytest.raises(DocumentOcrNotRetryable):
            repository.retry(
                job.tenant_id, job.project_id, job.document_id, 1, now
            )

        failed_job = _job(suffix, version=2, max_attempts=1)
        repository.request(failed_job)
        connection.commit()
        due = repository.claim_due(now + timedelta(hours=1), "live-worker", 5)
        target = next(item for item in due if item.version == 2)
        failed = repository.fail(target, detail="engine error", now=now)
        connection.commit()
        assert failed.status == "failed"
        assert failed.completed_at is not None

        requeued = repository.retry(
            job.tenant_id,
            job.project_id,
            job.document_id,
            2,
            now + timedelta(hours=2),
        )
        connection.commit()
        assert requeued.status == "pending"
        assert requeued.attempts == 0
        assert [item.version for item in repository.list(
            job.tenant_id, job.project_id, job.document_id
        )] == [1, 2]
