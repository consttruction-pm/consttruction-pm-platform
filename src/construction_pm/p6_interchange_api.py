from __future__ import annotations

from dataclasses import dataclass
import base64
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence
from uuid import uuid4

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_interchange_adapter import P6InterchangeAdapter, P6InterchangeCodec
from .p6_interchange_mapping import P6InterchangeCompatibilityError, P6InterchangeMapper
from .p6_mapping_registry import P6MappingFormat, P6MappingRegistryApplicationService
from .p6_interchange_import_ledger import (
    P6InterchangeImportBatch,
    P6InterchangeImportLedgerRepository,
    TARGET_APPLICATION_STATUS,
)

P6_INTERCHANGE_API_VERSION = "p6-interchange-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(policy: AuthorizationPolicy, auth_context: AuthorizationContext, permission: Permission) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


@dataclass(frozen=True)
class P6InterchangeAPI:
    mapping_service: P6MappingRegistryApplicationService
    authorization_policy: AuthorizationPolicy
    codecs: Mapping[P6MappingFormat, P6InterchangeCodec]
    import_ledger_repository: P6InterchangeImportLedgerRepository | None = None
    import_ledger_transaction_manager: object | None = None

    @staticmethod
    def _hash_value(value: object) -> str:
        try:
            encoded = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                default=lambda item: item.isoformat() if hasattr(item, "isoformat") else str(item),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("P6_INTERCHANGE_EVIDENCE_NOT_SERIALIZABLE") from exc
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _source_bytes(payload: Any) -> bytes:
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, str):
            return payload.encode("utf-8")
        try:
            return json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                default=lambda item: item.isoformat() if hasattr(item, "isoformat") else str(item),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("P6_INTERCHANGE_SOURCE_NOT_SERIALIZABLE") from exc

    def import_document(
        self,
        *,
        scope: BackendScope,
        format: P6MappingFormat,
        payload: Any,
        auth_context: AuthorizationContext,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        adapter = self._adapter(scope, format)
        source_rows, results = adapter.import_document_with_trace(payload, scope=scope)
        response = {
            "contract_version": P6_INTERCHANGE_API_VERSION,
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "format": format.value,
            "rows": [
                {"values": result.values, "extensions": result.extensions, "warnings": list(result.warnings)}
                for result in results
            ],
        }
        if self.import_ledger_repository is None:
            response["import_audit"] = {
                "status": "not_configured",
                "target_application_status": "not_configured",
                "batch_id": None,
            }
            return response
        if self.import_ledger_transaction_manager is None:
            raise ValueError("P6_INTERCHANGE_IMPORT_LEDGER_TRANSACTION_MANAGER_REQUIRED")
        mappings = self.mapping_service.list_mappings(scope, format=format)
        mapping_snapshot = tuple({
            "mapping_id": item.definition.mapping_id,
            "registry_version": item.definition.registry_version,
            "format": item.definition.format.value,
            "subject_area": item.definition.subject_area,
            "source_field": item.definition.source_field,
            "canonical_field": item.definition.canonical_field,
            "status": item.definition.status.value,
            "unit": item.definition.unit,
        } for item in mappings)
        row_summaries = tuple({
            "row_index": index,
            "source_fields": sorted(str(key) for key in source_row.values),
            "source_value_hashes": {
                str(key): self._hash_value(value)
                for key, value in sorted(source_row.values.items(), key=lambda pair: str(pair[0]))
            },
            "canonical_fields": sorted(str(key) for key in result.values),
            "canonical_value_hashes": {
                str(key): self._hash_value(value)
                for key, value in sorted(result.values.items(), key=lambda pair: str(pair[0]))
            },
            "preserved_extension_fields": sorted(str(key) for key in result.extensions),
            "extension_value_hashes": {
                str(key): self._hash_value(value)
                for key, value in sorted(result.extensions.items(), key=lambda pair: str(pair[0]))
            },
            "warnings": list(result.warnings),
        } for index, (source_row, result) in enumerate(zip(source_rows, results, strict=True)))
        source_bytes = self._source_bytes(payload)
        batch = P6InterchangeImportBatch(
            batch_id=str(uuid4()),
            scope=scope,
            request_key=idempotency_key,
            format=format.value,
            source_sha256=hashlib.sha256(source_bytes).hexdigest(),
            source_byte_count=len(source_bytes),
            row_count=len(results),
            mapping_snapshot=mapping_snapshot,
            row_summaries=row_summaries,
            imported_by=auth_context.user_id,
            imported_at=datetime.now(timezone.utc),
            target_application_status=TARGET_APPLICATION_STATUS,
        )
        with self.import_ledger_transaction_manager.transaction():
            saved = self.import_ledger_repository.record(batch)
        response["import_audit"] = {
            "status": "recorded",
            "batch_id": saved.batch_id,
            "source_sha256": saved.source_sha256,
            "row_count": saved.row_count,
            "mapping_count": len(saved.mapping_snapshot),
            "warning_count": sum(len(item.get("warnings", ())) for item in saved.row_summaries),
            "target_application_status": saved.target_application_status,
        }
        return response

    def list_import_batches(
        self,
        *,
        scope: BackendScope,
        auth_context: AuthorizationContext,
        limit: int = 100,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        if self.import_ledger_repository is None:
            return {
                "contract_version": P6_INTERCHANGE_API_VERSION,
                "scope": {
                    "tenant_id": scope.tenant_id,
                    "project_id": scope.project_id,
                    "project_revision": scope.project_revision,
                },
                "status": "not_configured",
                "batches": [],
            }
        if self.import_ledger_transaction_manager is None:
            raise ValueError("P6_INTERCHANGE_IMPORT_LEDGER_TRANSACTION_MANAGER_REQUIRED")
        with self.import_ledger_transaction_manager.transaction():
            batches = self.import_ledger_repository.list(scope, limit=limit)
        return {
            "contract_version": P6_INTERCHANGE_API_VERSION,
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "status": "available",
            "batches": [
                {
                    "batch_id": item.batch_id,
                    "format": item.format,
                    "source_sha256": item.source_sha256,
                    "source_byte_count": item.source_byte_count,
                    "row_count": item.row_count,
                    "mapping_count": len(item.mapping_snapshot),
                    "warning_count": sum(len(row.get("warnings", ())) for row in item.row_summaries),
                    "imported_by": item.imported_by,
                    "imported_at": item.imported_at.isoformat(),
                    "target_application_status": item.target_application_status,
                }
                for item in batches
            ],
        }

    def export_document(
        self,
        *,
        scope: BackendScope,
        format: P6MappingFormat,
        values: Sequence[Mapping[str, Any]],
        extensions: Sequence[Mapping[str, Any]] | None,
        auth_context: AuthorizationContext,
    ) -> Any:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        adapter = self._adapter(scope, format)
        document = adapter.export_document(values, scope=scope, extensions=extensions)
        if isinstance(document, bytes):
            document_payload: Any = {
                "encoding": "base64",
                "data": base64.b64encode(document).decode("ascii"),
            }
        elif isinstance(document, str):
            document_payload = {"encoding": "utf-8", "data": document}
        else:
            raise ValueError("UNSUPPORTED_INTERCHANGE_DOCUMENT_TYPE")
        return {
            "contract_version": P6_INTERCHANGE_API_VERSION,
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "format": format.value,
            "document": document_payload,
        }

    def _adapter(self, scope: BackendScope, format: P6MappingFormat) -> P6InterchangeAdapter:
        codec = self.codecs.get(format)
        if codec is None:
            raise ValueError("UNSUPPORTED_INTERCHANGE_FORMAT")
        mappings = self.mapping_service.list_mappings(scope, format=format)
        if not mappings:
            raise P6InterchangeCompatibilityError("MAPPING_REGISTRY_EMPTY")
        return P6InterchangeAdapter(
            mapper=P6InterchangeMapper(mappings),
            codec=codec,
        )


__all__ = ["P6_INTERCHANGE_API_VERSION", "P6InterchangeAPI"]
