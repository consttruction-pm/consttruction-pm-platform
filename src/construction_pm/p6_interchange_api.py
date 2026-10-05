from __future__ import annotations

from dataclasses import dataclass
import base64
from typing import Any, Mapping, Sequence

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_interchange_adapter import P6InterchangeAdapter, P6InterchangeCodec
from .p6_interchange_mapping import P6InterchangeCompatibilityError, P6InterchangeMapper
from .p6_mapping_registry import P6MappingFormat, P6MappingRegistryApplicationService

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

    def import_document(
        self,
        *,
        scope: BackendScope,
        format: P6MappingFormat,
        payload: Any,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        adapter = self._adapter(scope, format)
        results = adapter.import_document(payload, scope=scope)
        return {
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
