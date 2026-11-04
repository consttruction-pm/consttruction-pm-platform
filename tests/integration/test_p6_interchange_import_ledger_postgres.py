from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_import_ledger import (
    P6InterchangeImportBatch,
    P6InterchangeImportLedgerError,
    PostgresP6InterchangeImportLedgerRepository,
)


@pytest.fixture()
def postgres_connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    connection = psycopg.connect(dsn)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _batch(suffix: str) -> P6InterchangeImportBatch:
    scope = BackendScope(f"tenant-{suffix}", f"project-{suffix}", 4)
    return P6InterchangeImportBatch(
        batch_id=f"batch-{suffix}",
        scope=scope,
        request_key=f"request-{suffix}",
        format="XER_PROJECT",
        source_sha256="a" * 64,
        source_byte_count=450,
        row_count=1,
        mapping_snapshot=(
            {"mapping_id": "task-code", "source_field": "task_code", "status": "SUPPORTED"},
        ),
        row_summaries=(
            {
                "row_index": 0,
                "source_fields": ["task_code"],
                "canonical_fields": ["activity.activity_id"],
                "preserved_extension_fields": [],
                "warnings": [],
            },
        ),
        imported_by="admin-1",
        imported_at=datetime(2026, 11, 4, 21, 0, tzinfo=timezone.utc),
    )


def test_postgres_import_ledger_is_immutable_scoped_and_idempotent(postgres_connection) -> None:
    suffix = uuid4().hex
    candidate = _batch(suffix)
    with postgres_connection.transaction():
        repository = PostgresP6InterchangeImportLedgerRepository(postgres_connection)
        first = repository.record(candidate)
        retry = repository.record(
            P6InterchangeImportBatch(
                **{
                    **candidate.__dict__,
                    "batch_id": f"retry-{suffix}",
                    "imported_at": datetime(2026, 11, 4, 21, 5, tzinfo=timezone.utc),
                }
            )
        )
        assert retry.batch_id == first.batch_id
        assert retry.request_key == candidate.request_key
        assert retry.target_application_status == "PARSED_NOT_APPLIED"
        assert repository.get(candidate.scope, first.batch_id) == first
        assert repository.get(
            BackendScope(f"other-{suffix}", candidate.scope.project_id, 4), first.batch_id
        ) is None
        assert repository.list(candidate.scope) == (first,)

        changed = P6InterchangeImportBatch(
            **{
                **candidate.__dict__,
                "batch_id": f"changed-{suffix}",
                "source_sha256": "b" * 64,
            }
        )
        with pytest.raises(P6InterchangeImportLedgerError, match="P6_IMPORT_IDEMPOTENCY_KEY_REUSED"):
            repository.record(changed)

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="P6_INTERCHANGE_IMPORT_BATCH_IMMUTABLE",
        ):
            with postgres_connection.transaction():
                postgres_connection.execute(
                    "UPDATE p6_interchange_import_batch SET source_sha256=%s WHERE batch_id=%s",
                    ("c" * 64, first.batch_id),
                )
        with pytest.raises(
            psycopg.errors.RaiseException,
            match="P6_INTERCHANGE_IMPORT_BATCH_IMMUTABLE",
        ):
            with postgres_connection.transaction():
                postgres_connection.execute(
                    "DELETE FROM p6_interchange_import_batch WHERE batch_id=%s",
                    (first.batch_id,),
                )
