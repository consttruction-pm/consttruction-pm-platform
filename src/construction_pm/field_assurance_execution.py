from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .backend_p0.models import BackendScope
from .field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateInputType,
)


class FieldAssuranceExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class FieldAssuranceExecutionAnswer:
    item_id: str
    value: Any

    def validate(self, input_type: FieldAssuranceTemplateInputType, options: tuple[str, ...]) -> None:
        if not isinstance(self.item_id, str) or not self.item_id.strip():
            raise FieldAssuranceExecutionError("INVALID_EXECUTION_ITEM_ID")
        if input_type is FieldAssuranceTemplateInputType.BOOLEAN and not isinstance(self.value, bool):
            raise FieldAssuranceExecutionError("INVALID_BOOLEAN_ANSWER")
        if input_type is FieldAssuranceTemplateInputType.SELECT and (
            not isinstance(self.value, str) or self.value not in options
        ):
            raise FieldAssuranceExecutionError("INVALID_SELECT_ANSWER")
        if input_type is FieldAssuranceTemplateInputType.TEXT and (
            not isinstance(self.value, str)
        ):
            raise FieldAssuranceExecutionError("INVALID_TEXT_ANSWER")
        if input_type is FieldAssuranceTemplateInputType.NUMBER and (
            isinstance(self.value, bool) or not isinstance(self.value, (int, float))
        ):
            raise FieldAssuranceExecutionError("INVALID_NUMBER_ANSWER")


@dataclass(frozen=True)
class FieldAssuranceExecution:
    execution_id: str
    scope: BackendScope
    template_id: str
    template_version: int
    answers: tuple[FieldAssuranceExecutionAnswer, ...]
    executed_by: str
    executed_at: datetime
    contract_version: str = "field-assurance-execution.v1"

    def validate_against(self, template: FieldAssuranceTemplate) -> None:
        if self.contract_version != "field-assurance-execution.v1":
            raise FieldAssuranceExecutionError("UNSUPPORTED_EXECUTION_CONTRACT_VERSION")
        if not isinstance(self.execution_id, str) or not self.execution_id.strip():
            raise FieldAssuranceExecutionError("INVALID_EXECUTION_ID")
        if not isinstance(self.executed_by, str) or not self.executed_by.strip():
            raise FieldAssuranceExecutionError("INVALID_EXECUTED_BY")
        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise FieldAssuranceExecutionError("EXECUTED_AT_MUST_BE_TIMEZONE_AWARE")
        self.scope.validate()
        if self.scope != template.scope:
            raise FieldAssuranceExecutionError("EXECUTION_SCOPE_MISMATCH")
        if self.template_id != template.template_id or self.template_version != template.template_version:
            raise FieldAssuranceExecutionError("TEMPLATE_VERSION_MISMATCH")

        items = {item.item_id: item for item in template.items}
        if len(self.answers) > len(items):
            raise FieldAssuranceExecutionError("TOO_MANY_EXECUTION_ANSWERS")
        seen: set[str] = set()
        for answer in self.answers:
            if answer.item_id in seen:
                raise FieldAssuranceExecutionError("DUPLICATE_EXECUTION_ANSWER")
            seen.add(answer.item_id)
            item = items.get(answer.item_id)
            if item is None:
                raise FieldAssuranceExecutionError("UNKNOWN_EXECUTION_ITEM")
            answer.validate(item.input_type, item.options)

        missing = [
            item.item_id for item in sorted(template.items, key=lambda value: value.order)
            if item.required and item.item_id not in seen
        ]
        if missing:
            raise FieldAssuranceExecutionError(
                "MISSING_REQUIRED_EXECUTION_ANSWERS:" + ",".join(missing)
            )

    def as_dict(self) -> dict[str, Any]:
        self.scope.validate()
        return {
            "contract_version": self.contract_version,
            "execution_id": self.execution_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "template_id": self.template_id,
            "template_version": self.template_version,
            "answers": [
                {"item_id": answer.item_id, "value": answer.value}
                for answer in self.answers
            ],
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat(),
        }


class FieldAssuranceRepository(Protocol):
    def create_template(self, template: FieldAssuranceTemplate) -> FieldAssuranceTemplate: ...
    def get_template(
        self, scope: BackendScope, template_id: str, template_version: int
    ) -> FieldAssuranceTemplate | None: ...
    def execute(self, execution: FieldAssuranceExecution) -> FieldAssuranceExecution: ...
    def get_execution(
        self, scope: BackendScope, execution_id: str
    ) -> FieldAssuranceExecution | None: ...


class InMemoryFieldAssuranceRepository:
    """Atomic deterministic adapter used by application/integration tests."""

    def __init__(self) -> None:
        self._templates: dict[tuple[str, str, str, int], FieldAssuranceTemplate] = {}
        self._executions: dict[tuple[str, str, str], FieldAssuranceExecution] = {}

    def create_template(self, template: FieldAssuranceTemplate) -> FieldAssuranceTemplate:
        template.validate()
        key = (
            template.scope.tenant_id,
            template.scope.project_id,
            template.template_id,
            template.template_version,
        )
        if key in self._templates:
            raise FieldAssuranceExecutionError("TEMPLATE_VERSION_ALREADY_EXISTS")
        self._templates[key] = template
        return template

    def get_template(
        self, scope: BackendScope, template_id: str, template_version: int
    ) -> FieldAssuranceTemplate | None:
        scope.validate()
        return self._templates.get(
            (scope.tenant_id, scope.project_id, template_id, template_version)
        )

    def execute(self, execution: FieldAssuranceExecution) -> FieldAssuranceExecution:
        execution.scope.validate()
        key = (
            execution.scope.tenant_id,
            execution.scope.project_id,
            execution.execution_id,
        )
        if key in self._executions:
            raise FieldAssuranceExecutionError("EXECUTION_ALREADY_EXISTS")
        template = self.get_template(
            execution.scope, execution.template_id, execution.template_version
        )
        if template is None:
            raise FieldAssuranceExecutionError("TEMPLATE_NOT_FOUND")
        execution.validate_against(template)
        self._executions[key] = execution
        return execution

    def get_execution(
        self, scope: BackendScope, execution_id: str
    ) -> FieldAssuranceExecution | None:
        scope.validate()
        return self._executions.get(
            (scope.tenant_id, scope.project_id, execution_id)
        )


__all__ = [
    "FieldAssuranceExecution",
    "FieldAssuranceExecutionAnswer",
    "FieldAssuranceExecutionError",
    "FieldAssuranceRepository",
    "InMemoryFieldAssuranceRepository",
]
