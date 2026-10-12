from __future__ import annotations

import pytest

from construction_pm.p6_field_registry import P6FieldDefinition, P6FieldType
from construction_pm.p6_interchange_typed_conversion import (
    P6InterchangeTypedConversionError,
    typed_value_for_field,
)


@pytest.mark.parametrize(
    "field_type",
    [P6FieldType.STRING_ARRAY, P6FieldType.OBJECT_ID_ARRAY],
)
@pytest.mark.parametrize("raw", [[], ["first"], ["b", "a", "b"]])
def test_array_field_conversion_preserves_empty_values_and_order(field_type, raw):
    field = P6FieldDefinition(
        field_id="test.array",
        subject_area="Test",
        p6_field="ArrayValue",
        display_name="Array Value",
        data_type=field_type,
        writable=True,
        computed=False,
    )

    value = typed_value_for_field(field, raw)

    assert value.data_type == field_type.value
    assert value.value == raw
    assert value.value is not raw


@pytest.mark.parametrize(
    "field_type",
    [P6FieldType.STRING_ARRAY, P6FieldType.OBJECT_ID_ARRAY],
)
@pytest.mark.parametrize("raw", ["id-1,id-2", "id-1", [1], [None], [True]])
def test_array_field_conversion_rejects_scalar_csv_and_non_string_members(
    field_type, raw
):
    field = P6FieldDefinition(
        field_id="test.array",
        subject_area="Test",
        p6_field="ArrayValue",
        display_name="Array Value",
        data_type=field_type,
        writable=True,
        computed=False,
    )

    with pytest.raises(
        P6InterchangeTypedConversionError,
        match="INVALID_CANONICAL_VALUE:test.array:" + field_type.value,
    ):
        typed_value_for_field(field, raw)
