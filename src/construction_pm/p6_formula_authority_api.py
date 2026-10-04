from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_field_registry_repository import P6FieldRegistryApplicationService
from .p6_formula_engine import FormulaDefinition, FormulaError, FormulaSchemaValue, FormulaType, compile_formula
from .p6_formula_field_adapter import P6FormulaFieldAdapter


P6_FORMULA_AUTHORITY_API_VERSION = "p6-formula-authority-api.v1"

_FORMULA_TO_P6_TYPE = {
    FormulaType.TEXT: "string",
    FormulaType.NUMBER: "double",
    FormulaType.BOOLEAN: "boolean",
    FormulaType.DATE: "date",
    FormulaType.DATETIME: "datetime",
}

_CANDIDATE_TYPES = tuple(_FORMULA_TO_P6_TYPE)


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


@dataclass(frozen=True)
class P6FormulaAuthorityAPI:
    """Versioned API over the Shared Core formula validation authority."""

    field_service: P6FieldRegistryApplicationService
    authorization_policy: AuthorizationPolicy

    def validate(
        self,
        scope: BackendScope,
        registry_version: str,
        expression: str,
        *,
        auth_context: AuthorizationContext,
        context_field_id: str | None = None,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("authorization denied")

        fields = self.field_service.list_fields(scope, registry_version)
        schema = {
            record.field.field_id: P6FormulaFieldAdapter.schema_for_field(record.field)
            for record in fields
        }
        try:
            compiled = _compile_for_validation(expression, schema, context_field_id)
        except FormulaError as exc:
            return {
                "contract_version": P6_FORMULA_AUTHORITY_API_VERSION,
                "validation": {
                    "valid": False,
                    "error_code": str(exc) or exc.__class__.__name__.upper(),
                    "message_key": "p6.formula.validation.error",
                },
                "dependencies": {"field_ids": []},
                "result_type": {"data_type": None},
            }

        return {
            "contract_version": P6_FORMULA_AUTHORITY_API_VERSION,
            "validation": {"valid": True, "error_code": None, "message_key": None},
            "dependencies": {"field_ids": list(compiled.dependencies)},
            "result_type": {"data_type": _FORMULA_TO_P6_TYPE[compiled.inferred_type]},
        }


def _compile_for_validation(
    expression: str,
    schema: dict[str, FormulaSchemaValue],
    context_field_id: str | None,
):
    # Compile against each supported result type; Shared Core remains the
    # sole parser/type/dependency authority and determines the unique match.
    last_error: FormulaError | None = None
    for result_type in _CANDIDATE_TYPES:
        try:
            compiled = compile_formula(
                FormulaDefinition(
                    formula_id="__validation__",
                    version="1",
                    expression=expression,
                    result_type=result_type,
                ),
                schema,
            )
            if context_field_id and context_field_id in compiled.dependencies:
                raise FormulaError("FORMULA_SELF_REFERENCE")
            return compiled
        except FormulaError as exc:
            last_error = exc
    raise last_error or FormulaError("FORMULA_VALIDATION_FAILED")


__all__ = ["P6_FORMULA_AUTHORITY_API_VERSION", "P6FormulaAuthorityAPI"]
