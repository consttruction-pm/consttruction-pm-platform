from __future__ import annotations

"""Project-scoped formula columns backed by the Shared Formula Core.

A formula column is persisted through the existing formula-definition
repository and projected into the field registry as a computed Activity field.
Every displayed value is evaluated by the Python Shared Formula Core from the
persisted activity cells; the Web client never evaluates a formula. When a
formula cannot be evaluated for a row the cell stays empty instead of showing
an invented value.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_field_registry import P6FieldDefinition, P6FieldType
from .p6_field_registry_repository import (
    P6FieldRegistryApplicationService,
    PersistedP6Field,
)
from .p6_formula_definition_repository import (
    FormulaDefinitionCreateRequest,
    P6FormulaDefinitionApplicationService,
    PersistedP6FormulaDefinition,
)
from .p6_formula_dependency_graph import FormulaDependencyGraph
from .p6_formula_engine import (
    FormulaDefinition,
    FormulaError,
    FormulaSchemaValue,
    FormulaType,
    FormulaValue,
    compile_formula,
    evaluate_formula,
)
from .p6_formula_field_adapter import P6FormulaFieldAdapter, P6FormulaFieldTypeError

P6_FORMULA_COLUMN_API_VERSION = "p6-formula-column-api.v1"
P6_FORMULA_COLUMN_VERSION = "1"
_FORMULA_COLUMN_PREFIX = "formula."
_FORMULA_COLUMN_ID = re.compile(r"^formula\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*$")

_P6_TYPE_FOR_FORMULA: dict[FormulaType, P6FieldType] = {
    FormulaType.TEXT: P6FieldType.STRING,
    FormulaType.NUMBER: P6FieldType.DOUBLE,
    FormulaType.BOOLEAN: P6FieldType.BOOLEAN,
    FormulaType.DATE: P6FieldType.DATE,
    FormulaType.DATETIME: P6FieldType.DATETIME,
}
_CANDIDATE_TYPES = tuple(_P6_TYPE_FOR_FORMULA)
_DATA_TYPE_TEXT: dict[P6FieldType, str] = {
    P6FieldType.STRING: "text",
    P6FieldType.DATE: "date",
    P6FieldType.DATETIME: "datetime",
    P6FieldType.DURATION: "duration",
    P6FieldType.DECIMAL: "decimal",
    P6FieldType.PERCENTAGE: "percentage",
    P6FieldType.BOOLEAN: "boolean",
    P6FieldType.ENUM: "enum",
    P6FieldType.INTEGER: "integer",
    P6FieldType.DOUBLE: "double",
    P6FieldType.COST: "cost",
    P6FieldType.UNIT: "unit",
    P6FieldType.OBJECT_ID: "object-id",
    P6FieldType.OBJECT_ID_ARRAY: "object-id-array",
    P6FieldType.STRING_ARRAY: "string-array",
    P6FieldType.COMPLEX: "complex",
    P6FieldType.SPREAD: "spread",
}


class P6FormulaColumnError(ValueError):
    """Fail-closed error for formula-column validation and persistence."""


def _require_scope(scope: BackendScope, auth: AuthorizationContext) -> None:
    scope.validate()
    auth.validate()
    if scope.tenant_id != auth.tenant_id or scope.project_id != auth.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def normalize_formula_column_id(raw: str) -> str:
    value = raw.strip()
    if not _FORMULA_COLUMN_ID.fullmatch(value):
        raise P6FormulaColumnError("INVALID_FORMULA_COLUMN_ID")
    return value


def _schema(
    fields: tuple[PersistedP6Field, ...],
    formulas: tuple[PersistedP6FormulaDefinition, ...],
) -> tuple[dict[str, FormulaSchemaValue], dict[str, str]]:
    schema: dict[str, FormulaSchemaValue] = {}
    unsupported: dict[str, str] = {}
    for record in fields:
        try:
            schema[record.field.field_id] = P6FormulaFieldAdapter.schema_for_field(record.field)
        except P6FormulaFieldTypeError as exc:
            unsupported[record.field.field_id] = str(exc)
    for formula in formulas:
        schema[formula.formula_id] = FormulaSchemaValue(
            type=formula.definition.result_type,
            unit=formula.result_unit,
        )
    return schema, unsupported


def _compile_for_result(
    expression: str,
    schema: Mapping[str, FormulaSchemaValue],
    formula_id: str,
):
    last_error: FormulaError | None = None
    for result_type in _CANDIDATE_TYPES:
        try:
            compiled = compile_formula(
                FormulaDefinition(
                    formula_id=formula_id,
                    version=P6_FORMULA_COLUMN_VERSION,
                    expression=expression,
                    result_type=result_type,
                ),
                schema,
            )
        except FormulaError as exc:
            last_error = exc
            continue
        if formula_id in compiled.dependencies:
            raise P6FormulaColumnError("FORMULA_COLUMN_SELF_REFERENCE")
        return compiled
    raise P6FormulaColumnError(str(last_error) if last_error else "FORMULA_COLUMN_INVALID")


def _formula_field(record: PersistedP6FormulaDefinition) -> P6FieldDefinition:
    title = record.metadata.get("title")
    display_name = title.strip() if isinstance(title, str) and title.strip() else record.formula_id
    return P6FieldDefinition(
        field_id=record.formula_id,
        subject_area="Activity",
        p6_field=record.formula_id,
        display_name=display_name,
        data_type=_P6_TYPE_FOR_FORMULA[record.definition.result_type],
        writable=False,
        computed=True,
        unit=record.result_unit,
        source="CUBI formula column",
        reference_url="constructionpm://contracts/p6-formula-column/v1",
        read_only=True,
        disposition="implemented",
    )


def _to_formula_value(raw: object, schema: FormulaSchemaValue) -> FormulaValue:
    if raw is None:
        return FormulaValue.null()
    if schema.type is FormulaType.NUMBER:
        if isinstance(raw, bool):
            return FormulaValue.null()
        try:
            number = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return FormulaValue.null()
        if not number.is_finite():
            return FormulaValue.null()
        return FormulaValue.number(number, schema.unit)
    if schema.type is FormulaType.BOOLEAN:
        if isinstance(raw, bool):
            return FormulaValue.boolean(raw)
        return FormulaValue.null()
    if schema.type is FormulaType.DATE:
        try:
            return FormulaValue.date(date.fromisoformat(str(raw)))
        except (TypeError, ValueError):
            return FormulaValue.null()
    if schema.type is FormulaType.DATETIME:
        try:
            parsed = datetime.fromisoformat(str(raw))
        except (TypeError, ValueError):
            return FormulaValue.null()
        if parsed.tzinfo is None:
            return FormulaValue.null()
        return FormulaValue.datetime(parsed)
    return FormulaValue.text(str(raw))


def _display(value: FormulaValue) -> str | bool | None:
    if value.type is FormulaType.NULL:
        return None
    if value.type is FormulaType.BOOLEAN:
        return bool(value.value)
    if value.type is FormulaType.NUMBER:
        return format(value.value, "f")  # type: ignore[arg-type]
    return str(value.value)


def formula_column_dto(record: PersistedP6FormulaDefinition) -> dict[str, Any]:
    title = record.metadata.get("title")
    return {
        "contract_version": P6_FORMULA_COLUMN_API_VERSION,
        "kind": "formula_column",
        "scope": {
            "tenant_id": record.scope.tenant_id,
            "project_id": record.scope.project_id,
            "project_revision": record.scope.project_revision,
        },
        "formula": {
            "formula_id": record.formula_id,
            "version": record.version,
            "title": title if isinstance(title, str) and title.strip() else record.formula_id,
            "expression": record.definition.expression,
            "result_type": record.definition.result_type.value,
            "data_type": _DATA_TYPE_TEXT[_P6_TYPE_FOR_FORMULA[record.definition.result_type]],
            "result_unit": record.result_unit,
            "dependencies": list(record.dependencies),
        },
    }


@dataclass(frozen=True)
class P6FormulaColumnService:
    """Persist and evaluate project-scoped formula columns."""

    field_service: P6FieldRegistryApplicationService
    definition_service: P6FormulaDefinitionApplicationService
    registry_version: str = "p6-field-registry.v1"

    def list(self, scope: BackendScope) -> tuple[PersistedP6FormulaDefinition, ...]:
        return self.definition_service.list_all(scope)

    def field_record(
        self, scope: BackendScope, record: PersistedP6FormulaDefinition
    ) -> PersistedP6Field:
        return PersistedP6Field(
            scope=scope,
            registry_version=self.registry_version,
            field=_formula_field(record),
        )

    def field_records(
        self, scope: BackendScope
    ) -> tuple[PersistedP6Field, ...]:
        return tuple(self.field_record(scope, record) for record in self.list(scope))

    def create(
        self,
        scope: BackendScope,
        *,
        formula_id: str,
        title: str,
        expression: str,
    ) -> PersistedP6FormulaDefinition:
        normalized_id = normalize_formula_column_id(formula_id)
        clean_title = title.strip() if isinstance(title, str) else ""
        if not clean_title:
            raise P6FormulaColumnError("FORMULA_COLUMN_TITLE_REQUIRED")
        if len(clean_title) > 120:
            raise P6FormulaColumnError("FORMULA_COLUMN_TITLE_TOO_LONG")
        if not isinstance(expression, str) or not expression.strip():
            raise P6FormulaColumnError("FORMULA_COLUMN_EXPRESSION_REQUIRED")
        if not normalized_id.startswith(_FORMULA_COLUMN_PREFIX):
            raise P6FormulaColumnError("INVALID_FORMULA_COLUMN_ID")

        existing_formulas = self.list(scope)
        existing = next(
            (record for record in existing_formulas if record.formula_id == normalized_id),
            None,
        )
        if existing is not None:
            if existing.definition.expression == expression and existing.metadata.get("title") == clean_title:
                return existing
            raise P6FormulaColumnError("FORMULA_COLUMN_ALREADY_EXISTS")

        fields = self.field_service.list_fields(scope, self.registry_version)
        if any(record.field.field_id == normalized_id for record in fields):
            raise P6FormulaColumnError("FORMULA_COLUMN_ID_CONFLICT")

        schema, unsupported = _schema(fields, existing_formulas)
        try:
            compiled = _compile_for_result(expression, schema, normalized_id)
        except P6FormulaColumnError:
            raise
        except FormulaError as exc:
            raise P6FormulaColumnError(str(exc) or "FORMULA_COLUMN_INVALID") from exc
        for dependency in compiled.dependencies:
            if dependency in unsupported:
                raise P6FormulaColumnError(unsupported[dependency])
            if dependency not in schema:
                raise P6FormulaColumnError(f"UNKNOWN_FORMULA_FIELD:{dependency}")

        record = self.definition_service.create(
            FormulaDefinitionCreateRequest(
                scope=scope,
                semantic_version="cubi-formula-column.v1",
                semantic_reference="shared-core:p6-formula-column",
                formula_id=normalized_id,
                version=P6_FORMULA_COLUMN_VERSION,
                expression=expression,
                result_type=compiled.inferred_type,
                result_unit=None,
                dependencies=compiled.dependencies,
                metadata={
                    "subject_area": "Activity",
                    "title": clean_title,
                    "source": "cubi-formula-column",
                },
            )
        )
        return record

    def evaluate(
        self,
        scope: BackendScope,
        activity_cells: Mapping[str, Mapping[str, object]],
        formula_ids: tuple[str, ...] | list[str],
    ) -> Mapping[str, Mapping[str, str | bool | None]]:
        wanted = set(formula_ids)
        if not wanted:
            return {}
        definitions = tuple(record for record in self.list(scope) if record.formula_id in wanted)
        if not definitions:
            return {}
        fields = self.field_service.list_fields(scope, self.registry_version)
        schema, _unsupported = _schema(fields, self.list(scope))
        compiled = {}
        for record in definitions:
            try:
                compiled[record.formula_id] = compile_formula(
                    FormulaDefinition(
                        formula_id=record.formula_id,
                        version=record.version,
                        expression=record.definition.expression,
                        result_type=record.definition.result_type,
                    ),
                    schema,
                )
            except FormulaError:
                # A stored expression that no longer compiles stays blank; the
                # workspace never shows an invented value for it.
                continue
        if not compiled:
            return {}
        try:
            graph = FormulaDependencyGraph(compiled)
            ordered = graph.recalculation_plan(set(compiled)).ordered_formula_ids
        except FormulaError:
            return {}

        results: dict[str, dict[str, str | bool | None]] = {}
        for activity_id in sorted(activity_cells):
            cells = activity_cells[activity_id]
            values: dict[str, FormulaValue] = {
                field_id: _to_formula_value(cells.get(field_id), schema_value)
                for field_id, schema_value in schema.items()
                if field_id not in compiled
            }
            row: dict[str, str | bool | None] = {}
            for formula_id in ordered:
                try:
                    value = evaluate_formula(compiled[formula_id], values)
                except FormulaError:
                    continue
                values[formula_id] = value
                row[formula_id] = _display(value)
            results[activity_id] = row
        return results


@dataclass(frozen=True)
class P6FormulaColumnAPI:
    service: P6FormulaColumnService
    authorization_policy: AuthorizationPolicy
    registry_version: str = "p6-field-registry.v1"

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(formula_column_dto(record) for record in self.service.list(scope))

    def create(
        self,
        scope: BackendScope,
        *,
        formula_id: str,
        title: str,
        expression: str,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        record = self.service.create(
            scope,
            formula_id=formula_id,
            title=title,
            expression=expression,
        )
        return formula_column_dto(record)


__all__ = [
    "P6_FORMULA_COLUMN_API_VERSION",
    "P6FormulaColumnAPI",
    "P6FormulaColumnError",
    "P6FormulaColumnService",
    "formula_column_dto",
    "normalize_formula_column_id",
]
