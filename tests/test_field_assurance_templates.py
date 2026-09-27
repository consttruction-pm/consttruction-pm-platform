from __future__ import annotations

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.field_assurance_templates import (
    FieldAssuranceTemplate,
    FieldAssuranceTemplateError,
    FieldAssuranceTemplateInputType,
    FieldAssuranceTemplateItem,
    FieldAssuranceTemplateType,
)


def scope(revision: int = 4) -> BackendScope:
    return BackendScope("tenant-1", "project-1", revision)


def template(*, revision: int = 4) -> FieldAssuranceTemplate:
    return FieldAssuranceTemplate(
        template_id="TPL-1",
        scope=scope(revision),
        template_version=2,
        template_type=FieldAssuranceTemplateType.INSPECTION,
        title_key="inspection.concrete",
        items=(
            FieldAssuranceTemplateItem(
                "I-2", 2, "criterion.finish", FieldAssuranceTemplateInputType.SELECT, True, ("pass", "fail", "na")
            ),
            FieldAssuranceTemplateItem(
                "I-1", 1, "criterion.dimension", FieldAssuranceTemplateInputType.NUMBER, True
            ),
        ),
    )


def test_template_is_immutable_and_serialization_is_deterministic() -> None:
    value = template()
    first = value.as_dict()
    second = value.as_dict()

    assert first == second
    assert [item["item_id"] for item in first["items"]] == ["I-1", "I-2"]
    assert first["scope"]["project_revision"] == 4
    with pytest.raises(Exception):
        value.items = ()  # type: ignore[misc]


@pytest.mark.parametrize(
    "item, error",
    [
        (
            FieldAssuranceTemplateItem(
                "I-1", 1, "criterion", FieldAssuranceTemplateInputType.SELECT, True, ()
            ),
            "SELECT_TEMPLATE_ITEM_OPTIONS_REQUIRED",
        ),
        (
            FieldAssuranceTemplateItem(
                "I-1", 1, "criterion", FieldAssuranceTemplateInputType.TEXT, False, ("unexpected",)
            ),
            "OPTIONS_ONLY_ALLOWED_FOR_SELECT",
        ),
        (
            FieldAssuranceTemplateItem(
                "I-1", 1, "criterion", FieldAssuranceTemplateInputType.SELECT, False, ("x", "x")
            ),
            "DUPLICATE_TEMPLATE_ITEM_OPTION",
        ),
    ],
)
def test_item_validation_is_strict(item: FieldAssuranceTemplateItem, error: str) -> None:
    with pytest.raises(FieldAssuranceTemplateError, match=error):
        item.validate()


def test_duplicate_item_ids_are_rejected() -> None:
    value = template()
    duplicate = FieldAssuranceTemplate(
        value.template_id,
        value.scope,
        value.template_version,
        value.template_type,
        value.title_key,
        (
            value.items[0],
            FieldAssuranceTemplateItem(
                "I-2", 1, "criterion.other", FieldAssuranceTemplateInputType.TEXT, False
            ),
        ),
    )
    with pytest.raises(FieldAssuranceTemplateError, match="DUPLICATE_TEMPLATE_ITEM_ID"):
        duplicate.validate()


def test_item_order_must_be_contiguous() -> None:
    value = template()
    invalid = FieldAssuranceTemplate(
        value.template_id,
        value.scope,
        value.template_version,
        value.template_type,
        value.title_key,
        (
            FieldAssuranceTemplateItem(
                "I-1", 1, "criterion.one", FieldAssuranceTemplateInputType.TEXT, True
            ),
            FieldAssuranceTemplateItem(
                "I-3", 3, "criterion.three", FieldAssuranceTemplateInputType.TEXT, True
            ),
        ),
    )
    with pytest.raises(FieldAssuranceTemplateError, match="NON_CONTIGUOUS_TEMPLATE_ITEM_ORDER"):
        invalid.validate()


def test_invalid_contract_version_is_rejected() -> None:
    value = template()
    invalid = FieldAssuranceTemplate(
        value.template_id,
        value.scope,
        value.template_version,
        value.template_type,
        value.title_key,
        value.items,
        contract_version="field-assurance-template.v2",
    )
    with pytest.raises(FieldAssuranceTemplateError, match="UNSUPPORTED_TEMPLATE_CONTRACT_VERSION"):
        invalid.validate()


def test_revision_mismatch_is_rejected() -> None:
    current = template(revision=4)
    current.require_scope(scope(4))
    with pytest.raises(FieldAssuranceTemplateError, match="TEMPLATE_SCOPE_MISMATCH"):
        current.require_scope(scope(5))
