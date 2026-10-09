from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_interchange_mapping import (
    P6InterchangeCompatibilityError,
    P6InterchangeMapper,
    P6InterchangeRow,
)
from construction_pm.p6_interchange_typed_conversion import (
    P6InterchangeTypedConversionError,
    typed_value_for_field,
)
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)


def test_integer_conversion_accepts_lossless_integer_representations() -> None:
    field = get_field("activity.float_path")

    assert typed_value_for_field(field, "42").value == 42
    assert typed_value_for_field(field, Decimal("42.000")).value == 42
    assert typed_value_for_field(field, 42).value == 42


@pytest.mark.parametrize("raw", [3.9, "3.9", Decimal("3.9"), True, "NaN", "Infinity"])
def test_integer_conversion_rejects_fractional_boolean_or_non_finite_values(raw) -> None:
    with pytest.raises(
        P6InterchangeTypedConversionError,
        match="INVALID_CANONICAL_VALUE:activity.float_path:integer",
    ):
        typed_value_for_field(get_field("activity.float_path"), raw)


def test_import_rejects_fractional_value_in_integer_canonical_field() -> None:
    scope = BackendScope(tenant_id="t1", project_id="p1", project_revision=4)
    mapping = PersistedP6Mapping(
        scope=scope,
        definition=P6MappingDefinition(
            mapping_id="activity.float_path",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="float_path",
            canonical_field="activity.float_path",
            status=P6MappingStatus.SUPPORTED,
            canonical_type="integer",
        ),
    )
    mapper = P6InterchangeMapper((mapping,))

    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="INVALID_CANONICAL_VALUE:activity.float_path:integer",
    ):
        mapper.import_row(
            P6InterchangeRow(
                scope=scope,
                format=P6MappingFormat.XER_PROJECT,
                values={"float_path": "3.9"},
            )
        )
