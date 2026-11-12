from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_field_registry import P6FieldType
from .p6_user_defined_field_values_repository import (
    P6DurationValue,
    P6UserDefinedFieldValue,
    P6UserDefinedFieldValueApplicationService,
    P6UserDefinedFieldValuePersistenceError,
)
from .p6_user_defined_fields_repository import P6UserDefinedFieldDefinition


P6_UDF_VALUE_API_VERSION = "p6-udf-value-api.v1"
P6_UDF_VALUE_REGISTRY_VERSION = "p6-field-registry.v1"
P6_UDF_VALUE_OBJECT_TYPE = "activity"

_SUBJECT_OBJECT_TYPES = {"activity": "activity"}


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def _require_object_type(object_type: str) -> str:
    normalized = object_type.strip().lower() if isinstance(object_type, str) else ""
    if normalized not in _SUBJECT_OBJECT_TYPES:
        raise P6UserDefinedFieldValuePersistenceError("UNSUPPORTED_UDF_OBJECT_TYPE")
    return normalized


def _require_object_id(object_id: str) -> str:
    if not isinstance(object_id, str) or not object_id.strip():
        raise P6UserDefinedFieldValuePersistenceError("INVALID_OBJECT_ID")
    return object_id.strip()


def _coerce_value(definition: P6UserDefinedFieldDefinition, raw: object) -> object:
    """Convert the JSON request value into the typed value the repository stores."""

    if raw is None:
        if not definition.nullable:
            raise P6UserDefinedFieldValuePersistenceError("INVALID_NULL_VALUE")
        return None
    kind = definition.data_type
    if kind is P6FieldType.STRING:
        if not isinstance(raw, str):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_STRING_VALUE")
        return raw
    if kind is P6FieldType.DATE:
        if not isinstance(raw, str):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DATE_VALUE")
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DATE_VALUE") from exc
    if kind is P6FieldType.DATETIME:
        if not isinstance(raw, str):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DATETIME_VALUE")
        try:
            result = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DATETIME_VALUE") from exc
        if result.tzinfo is None or result.utcoffset() is None:
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DATETIME_VALUE")
        return result
    if kind in {
        P6FieldType.DECIMAL,
        P6FieldType.DOUBLE,
        P6FieldType.COST,
        P6FieldType.PERCENTAGE,
    }:
        if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DECIMAL_VALUE")
        try:
            result = Decimal(str(raw))
        except InvalidOperation as exc:
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DECIMAL_VALUE") from exc
        if not result.is_finite():
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DECIMAL_VALUE")
        return result
    if kind is P6FieldType.INTEGER:
        if isinstance(raw, bool):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_INTEGER_VALUE")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw.strip().lstrip("-").isdigit():
            return int(raw.strip())
        raise P6UserDefinedFieldValuePersistenceError("INVALID_INTEGER_VALUE")
    if kind is P6FieldType.BOOLEAN:
        if not isinstance(raw, bool):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_BOOLEAN_VALUE")
        return raw
    if kind is P6FieldType.ENUM:
        if not isinstance(raw, str) or raw not in definition.allowed_values:
            raise P6UserDefinedFieldValuePersistenceError("INVALID_ENUM_VALUE")
        return raw
    if kind is P6FieldType.DURATION:
        if not isinstance(raw, dict):
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DURATION_VALUE")
        try:
            duration = P6DurationValue(Decimal(str(raw["value"])), str(raw["unit"]))
        except (KeyError, TypeError, InvalidOperation) as exc:
            raise P6UserDefinedFieldValuePersistenceError("INVALID_DURATION_VALUE") from exc
        duration.validate()
        return duration
    raise P6UserDefinedFieldValuePersistenceError("UNSUPPORTED_TYPED_UDF_VALUE")


def _json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, P6DurationValue):
        return {"value": str(value.value), "unit": value.unit}
    return value


def _definition_dto(definition: P6UserDefinedFieldDefinition) -> dict[str, Any]:
    return {
        "udf_id": definition.udf_id,
        "subject_area": definition.subject_area,
        "display_name": definition.display_name,
        "data_type": definition.data_type.value,
        "writable": definition.writable,
        "nullable": definition.nullable,
        "unit": definition.unit,
        "allowed_values": list(definition.allowed_values),
    }


@dataclass(frozen=True)
class P6UserDefinedFieldValueAPI:
    """Typed activity UDF values behind project read/write authorization.

    Definitions and values stay revision-scoped in the repository. This API
    never evaluates or derives a value; it only validates the request against
    the stored definition and delegates persistence to the application service.
    """

    value_service: P6UserDefinedFieldValueApplicationService
    authorization_policy: AuthorizationPolicy

    def read_values(
        self,
        scope: BackendScope,
        registry_version: str,
        object_type: str,
        object_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        normalized = _require_object_type(object_type)
        object_id = _require_object_id(object_id)
        if registry_version != P6_UDF_VALUE_REGISTRY_VERSION:
            raise P6UserDefinedFieldValuePersistenceError("UNSUPPORTED_REGISTRY_VERSION")
        definitions = self.value_service.definition_repository.list_definitions(
            scope, registry_version, None
        )
        values: list[dict[str, Any]] = []
        for definition in definitions:
            if definition.subject_area.lower() != normalized:
                continue
            loaded = self.value_service.read_value(scope, definition.udf_id, normalized, object_id)
            values.append({
                "contract_version": P6_UDF_VALUE_API_VERSION,
                "kind": "user_defined_field_value",
                "object_type": normalized,
                "object_id": object_id,
                "scope": {
                    "tenant_id": scope.tenant_id,
                    "project_id": scope.project_id,
                    "project_revision": scope.project_revision,
                },
                **_definition_dto(definition),
                "value": _json_value(loaded.value if loaded is not None else None),
            })
        return tuple(values)

    def save_value(
        self,
        scope: BackendScope,
        registry_version: str,
        object_type: str,
        object_id: str,
        udf_id: str,
        raw_value: object,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        normalized = _require_object_type(object_type)
        object_id = _require_object_id(object_id)
        if registry_version != P6_UDF_VALUE_REGISTRY_VERSION:
            raise P6UserDefinedFieldValuePersistenceError("UNSUPPORTED_REGISTRY_VERSION")
        if not isinstance(udf_id, str) or not udf_id.strip():
            raise P6UserDefinedFieldValuePersistenceError("INVALID_UDF_ID")
        udf_id = udf_id.strip()
        definition = self.value_service.definition_repository.get_definition(
            scope, registry_version, udf_id
        )
        if definition is None or definition.subject_area.lower() != normalized:
            raise P6UserDefinedFieldValuePersistenceError("UDF_NOT_FOUND")
        if not definition.writable:
            raise P6UserDefinedFieldValuePersistenceError("UDF_NOT_WRITABLE")
        value = P6UserDefinedFieldValue(
            scope=scope,
            udf_id=udf_id,
            object_type=normalized,
            object_id=object_id,
            value=_coerce_value(definition, raw_value),
        )
        saved = self.value_service.save_value(value)
        return {
            "contract_version": P6_UDF_VALUE_API_VERSION,
            "kind": "user_defined_field_value",
            "object_type": normalized,
            "object_id": object_id,
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            **_definition_dto(definition),
            "value": _json_value(saved.value),
        }


__all__ = [
    "P6_UDF_VALUE_API_VERSION",
    "P6_UDF_VALUE_OBJECT_TYPE",
    "P6_UDF_VALUE_REGISTRY_VERSION",
    "P6UserDefinedFieldValueAPI",
]
