from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .backend_p0.models import BackendScope, MAX_SAFE_REVISION


class FieldAssuranceTemplateError(ValueError):
    pass


class FieldAssuranceTemplateType(str, Enum):
    INSPECTION = "inspection"
    QUALITY = "quality"
    SAFETY = "safety"


class FieldAssuranceTemplateInputType(str, Enum):
    BOOLEAN = "boolean"
    SELECT = "select"
    TEXT = "text"
    NUMBER = "number"


@dataclass(frozen=True)
class FieldAssuranceTemplateItem:
    item_id: str
    order: int
    criterion_key: str
    input_type: FieldAssuranceTemplateInputType
    required: bool
    options: tuple[str, ...] = ()

    def validate(self) -> None:
        if not isinstance(self.item_id, str) or not self.item_id.strip():
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_ITEM_ID")
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 1:
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_ITEM_ORDER")
        if not isinstance(self.criterion_key, str) or not self.criterion_key.strip():
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_ITEM_CRITERION")
        if not isinstance(self.input_type, FieldAssuranceTemplateInputType):
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_ITEM_INPUT_TYPE")
        if not isinstance(self.required, bool):
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_ITEM_REQUIRED")
        if any(not isinstance(option, str) or not option.strip() for option in self.options):
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_ITEM_OPTION")
        if len(set(self.options)) != len(self.options):
            raise FieldAssuranceTemplateError("DUPLICATE_TEMPLATE_ITEM_OPTION")
        if self.input_type is FieldAssuranceTemplateInputType.SELECT and not self.options:
            raise FieldAssuranceTemplateError("SELECT_TEMPLATE_ITEM_OPTIONS_REQUIRED")
        if self.input_type is not FieldAssuranceTemplateInputType.SELECT and self.options:
            raise FieldAssuranceTemplateError("OPTIONS_ONLY_ALLOWED_FOR_SELECT")

    def require_scope(self, expected_scope: BackendScope) -> None:
        self.validate()
        if not isinstance(expected_scope, BackendScope):
            raise FieldAssuranceTemplateError("INVALID_EXPECTED_TEMPLATE_SCOPE")
        expected_scope.validate()
        if self.scope != expected_scope:
            raise FieldAssuranceTemplateError("TEMPLATE_SCOPE_MISMATCH")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "item_id": self.item_id,
            "order": self.order,
            "criterion_key": self.criterion_key,
            "input_type": self.input_type.value,
            "required": self.required,
            **({"options": list(self.options)} if self.options else {}),
        }


@dataclass(frozen=True)
class FieldAssuranceTemplate:
    template_id: str
    scope: BackendScope
    template_version: int
    template_type: FieldAssuranceTemplateType
    title_key: str
    items: tuple[FieldAssuranceTemplateItem, ...]
    contract_version: str = "field-assurance-template.v1"

    def validate(self) -> None:
        if self.contract_version != "field-assurance-template.v1":
            raise FieldAssuranceTemplateError("UNSUPPORTED_TEMPLATE_CONTRACT_VERSION")
        if not isinstance(self.template_id, str) or not self.template_id.strip():
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_ID")
        self.scope.validate()
        if isinstance(self.template_version, bool) or not isinstance(self.template_version, int) or not 1 <= self.template_version <= MAX_SAFE_REVISION:
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_VERSION")
        if not isinstance(self.template_type, FieldAssuranceTemplateType):
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_TYPE")
        if not isinstance(self.title_key, str) or not self.title_key.strip():
            raise FieldAssuranceTemplateError("INVALID_TEMPLATE_TITLE")
        if not self.items:
            raise FieldAssuranceTemplateError("TEMPLATE_ITEMS_REQUIRED")

        seen_ids: set[str] = set()
        orders: list[int] = []
        for item in self.items:
            item.validate()
            if item.item_id in seen_ids:
                raise FieldAssuranceTemplateError("DUPLICATE_TEMPLATE_ITEM_ID")
            seen_ids.add(item.item_id)
            orders.append(item.order)
        if len(set(orders)) != len(orders):
            raise FieldAssuranceTemplateError("DUPLICATE_TEMPLATE_ITEM_ORDER")
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise FieldAssuranceTemplateError("NON_CONTIGUOUS_TEMPLATE_ITEM_ORDER")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "template_id": self.template_id,
            "scope": {
                "tenant_id": self.scope.tenant_id,
                "project_id": self.scope.project_id,
                "project_revision": self.scope.project_revision,
            },
            "template_version": self.template_version,
            "template_type": self.template_type.value,
            "title_key": self.title_key,
            "items": [item.as_dict() for item in sorted(self.items, key=lambda value: value.order)],
        }


__all__ = [
    "FieldAssuranceTemplate",
    "FieldAssuranceTemplateError",
    "FieldAssuranceTemplateInputType",
    "FieldAssuranceTemplateItem",
    "FieldAssuranceTemplateType",
]
