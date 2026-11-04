from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_import_ledger import (
    P6InterchangeImportBatch,
    P6InterchangeImportLedgerError,
    SQLiteP6InterchangeImportLedgerRepository,
    TARGET_APPLICATION_STATUS,
)


NOW = datetime(2026, 11, 4, 20, 0, tzinfo=timezone.utc)
SCOPE = BackendScope("tenant-1", "project-1", 9)


def batch(
    *,
    batch_id: str = "batch-1",
    request_key: str | None = "request-1",
    source_sha256: str = "a" * 64,
) -> P6InterchangeImportBatch:
    return P6InterchangeImportBatch(
        batch_id=batch_id,
        scope=SCOPE,
        request_key=request_key,
        format="XER_PROJECT",
        source_sha256=source_sha256,
        source_byte_count=123,
        row_count=1,
        mapping_snapshot=(
            {
                "mapping_id": "activity.code",
                "registry_version": "p6-field-registry.v1",
                "source_field": "task_code",
                "canonical_field": "activity.code",
                "status": "SUPPORTED",
            },
        ),
        row_summaries=(
            {
                "row_index": 0,
                "source_fields": ["task_code", "vendor_ext"],
                "source_value_hashes": {"task_code": "b" * 64, "vendor_ext": "c" * 64},
                "canonical_fields": ["activity.code"],
                "canonical_value_hashes": {"activity.code": "d" * 64},
                "preserved_extension_fields": ["p6.interchange.tenant.project.vendor_ext"],
                "extension_value_hashes": {"p6.interchange.tenant.project.vendor_ext": "c" * 64},
                "warnings": ["PRESERVED_UNKNOWN_FIELD:vendor_ext"],
            },
        ),
        imported_by="user-1",
        imported_at=NOW,
        target_application_status=TARGET_APPLICATION_STATUS,
    )


def test_import_ledger_is_immutable_idempotent_and_project_scoped() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteP6InterchangeImportLedgerRepository(connection)
        first = repository.record(batch())
        replay = repository.record(batch(batch_id="batch-retry"))

        assert replay.batch_id == first.batch_id
        assert replay.source_sha256 == "a" * 64
        assert replay.row_count == 1
        assert replay.target_application_status == "PARSED_NOT_APPLIED"
        assert repository.get(SCOPE, first.batch_id) == first
        assert repository.get(BackendScope("tenant-2", "project-1", 9), first.batch_id) is None
        assert repository.get(BackendScope("tenant-1", "project-2", 9), first.batch_id) is None
        assert repository.list(SCOPE) == (first,)
        assert repository.list(BackendScope("tenant-2", "project-1", 9)) == ()

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE p6_interchange_import_batch SET source_sha256=? WHERE batch_id=?",
                ("e" * 64, first.batch_id),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "DELETE FROM p6_interchange_import_batch WHERE batch_id=?",
                (first.batch_id,),
            )
    finally:
        connection.close()


def test_import_ledger_idempotency_key_reuse_with_different_source_fails_closed() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteP6InterchangeImportLedgerRepository(connection)
        repository.record(batch())
        with pytest.raises(P6InterchangeImportLedgerError, match="P6_IMPORT_IDEMPOTENCY_KEY_REUSED"):
            repository.record(batch(batch_id="batch-2", source_sha256="f" * 64))
    finally:
        connection.close()


def test_import_ledger_validates_row_count_hash_and_request_key() -> None:
    with pytest.raises(P6InterchangeImportLedgerError, match="ROW_SUMMARY_COUNT_MISMATCH"):
        P6InterchangeImportBatch(
            batch_id="batch-bad",
            scope=SCOPE,
            request_key=None,
            format="XER_PROJECT",
            source_sha256="a" * 64,
            source_byte_count=123,
            row_count=2,
            mapping_snapshot=(),
            row_summaries=(),
            imported_by="user-1",
            imported_at=NOW,
        ).validate()
    with pytest.raises(P6InterchangeImportLedgerError, match="SOURCE_HASH_INVALID"):
        P6InterchangeImportBatch(
            batch_id="batch-bad",
            scope=SCOPE,
            request_key=None,
            format="XER_PROJECT",
            source_sha256="invalid",
            source_byte_count=123,
            row_count=0,
            mapping_snapshot=(),
            row_summaries=(),
            imported_by="user-1",
            imported_at=NOW,
        ).validate()
