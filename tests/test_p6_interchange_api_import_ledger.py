from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import sqlite3
from typing import Any, Sequence

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_interchange_api import P6InterchangeAPI
from construction_pm.p6_interchange_import_ledger import SQLiteP6InterchangeImportLedgerRepository
from construction_pm.p6_interchange_mapping import P6InterchangeResult, P6InterchangeRow
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)


SCOPE = BackendScope("tenant-1", "project-1", 9)
ADMIN = AuthorizationContext("tenant-1", "project-1", "admin-1", frozenset({"project_admin"}))
NOW = datetime(2026, 11, 4, 20, 0, tzinfo=timezone.utc)


class MappingService:
    def __init__(self):
        self.mappings = (
            PersistedP6Mapping(
                scope=SCOPE,
                definition=P6MappingDefinition(
                    mapping_id="activity.code",
                    registry_version="p6-field-registry.v1",
                    format=P6MappingFormat.XER_PROJECT,
                    subject_area="Activity",
                    source_field="task_code",
                    canonical_field="activity.activity_name",
                    status=P6MappingStatus.SUPPORTED,
                    canonical_type="string",
                ),
            ),
        )

    def list_mappings(self, scope, *, format=None, subject_area=None):
        return tuple(item for item in self.mappings if format is None or item.definition.format == format)


@dataclass
class Codec:
    format: P6MappingFormat = P6MappingFormat.XER_PROJECT

    def decode(self, payload: Any, scope: BackendScope) -> Sequence[P6InterchangeRow]:
        return (
            P6InterchangeRow(
                scope=scope,
                format=self.format,
                values={"task_code": "A-10", "vendor_cost_code": "CC-7"},
                extensions={"codec.note": "parsed"},
            ),
        )

    def encode(self, rows: Sequence[P6InterchangeResult], scope: BackendScope) -> Any:
        return {"rows": [row.values for row in rows]}


def test_import_api_persists_hash_mapping_coverage_and_row_evidence_idempotently() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        repository = SQLiteP6InterchangeImportLedgerRepository(connection)
        api = P6InterchangeAPI(
            mapping_service=MappingService(),
            authorization_policy=default_project_policy(),
            codecs={P6MappingFormat.XER_PROJECT: Codec()},
            import_ledger_repository=repository,
            import_ledger_transaction_manager=SQLiteTransactionManager(connection),
        )
        source = b"raw-xer-document"
        first = api.import_document(
            scope=SCOPE,
            format=P6MappingFormat.XER_PROJECT,
            payload=source,
            auth_context=ADMIN,
            idempotency_key="req-100",
        )
        replay = api.import_document(
            scope=SCOPE,
            format=P6MappingFormat.XER_PROJECT,
            payload=source,
            auth_context=ADMIN,
            idempotency_key="req-100",
        )

        audit = first["import_audit"]
        assert audit["status"] == "recorded"
        assert audit["target_application_status"] == "PARSED_NOT_APPLIED"
        assert audit["source_sha256"] == hashlib.sha256(source).hexdigest()
        assert audit["row_count"] == 1
        assert audit["warning_count"] == 1
        assert replay["import_audit"]["batch_id"] == audit["batch_id"]
        assert first["rows"][0]["values"] == {"activity.activity_name": "A-10"}
        assert "PRESERVED_UNKNOWN_FIELD:vendor_cost_code" in first["rows"][0]["warnings"]

        history = api.list_import_batches(scope=SCOPE, auth_context=ADMIN)
        assert history["status"] == "available"
        assert len(history["batches"]) == 1
        assert history["batches"][0]["batch_id"] == audit["batch_id"]
        assert history["batches"][0]["target_application_status"] == "PARSED_NOT_APPLIED"

        stored = repository.get(SCOPE, audit["batch_id"])
        assert stored is not None
        assert stored.row_summaries[0]["source_fields"] == ["task_code", "vendor_cost_code"]
        assert stored.row_summaries[0]["canonical_fields"] == ["activity.activity_name"]
        assert any("vendor_cost_code" in field for field in stored.row_summaries[0]["preserved_extension_fields"])
    finally:
        connection.close()


def test_import_api_fails_closed_when_idempotency_key_is_reused_for_other_source() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        api = P6InterchangeAPI(
            mapping_service=MappingService(),
            authorization_policy=default_project_policy(),
            codecs={P6MappingFormat.XER_PROJECT: Codec()},
            import_ledger_repository=SQLiteP6InterchangeImportLedgerRepository(connection),
            import_ledger_transaction_manager=SQLiteTransactionManager(connection),
        )
        api.import_document(
            scope=SCOPE, format=P6MappingFormat.XER_PROJECT, payload=b"source-A",
            auth_context=ADMIN, idempotency_key="same-key",
        )
        with pytest.raises(ValueError, match="P6_IMPORT_IDEMPOTENCY_KEY_REUSED"):
            api.import_document(
                scope=SCOPE, format=P6MappingFormat.XER_PROJECT, payload=b"source-B",
                auth_context=ADMIN, idempotency_key="same-key",
            )
    finally:
        connection.close()


def test_import_ledger_list_requires_project_read_scope() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        api = P6InterchangeAPI(
            mapping_service=MappingService(),
            authorization_policy=default_project_policy(),
            codecs={P6MappingFormat.XER_PROJECT: Codec()},
            import_ledger_repository=SQLiteP6InterchangeImportLedgerRepository(connection),
            import_ledger_transaction_manager=SQLiteTransactionManager(connection),
        )
        other = AuthorizationContext("tenant-2", "project-1", "viewer", frozenset({"viewer"}))
        with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
            api.list_import_batches(scope=SCOPE, auth_context=other)
    finally:
        connection.close()
