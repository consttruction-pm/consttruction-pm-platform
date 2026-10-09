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


def test_decimal_conversion_preserves_finite_precision() -> None:
    value = typed_value_for_field(
        get_field("activity.earned_value_cost"), "123.4500"
    )
    assert value.value == Decimal("123.4500")


@pytest.mark.parametrize(
    "raw",
    ["NaN", "Infinity", "-Infinity", Decimal("NaN"), Decimal("Infinity")],
)
def test_decimal_conversion_rejects_non_finite_values(raw) -> None:
    with pytest.raises(
        P6InterchangeTypedConversionError,
        match="INVALID_CANONICAL_VALUE:activity.earned_value_cost:double",
    ):
        typed_value_for_field(get_field("activity.earned_value_cost"), raw)


def test_import_rejects_non_finite_value_in_canonical_decimal_field() -> None:
    scope = BackendScope(tenant_id="t1", project_id="p1", project_revision=4)
    mapping = PersistedP6Mapping(
        scope=scope,
        definition=P6MappingDefinition(
            mapping_id="activity.earned_value_cost",
            registry_version="p6-field-registry.v1",
            format=P6MappingFormat.XER_PROJECT,
            subject_area="Activity",
            source_field="ev",
            canonical_field="activity.earned_value_cost",
            status=P6MappingStatus.SUPPORTED,
            canonical_type="double",
        ),
    )
    mapper = P6InterchangeMapper((mapping,))

    with pytest.raises(
        P6InterchangeCompatibilityError,
        match="INVALID_CANONICAL_VALUE:activity.earned_value_cost:double",
    ):
        mapper.import_row(
            P6InterchangeRow(
                scope=scope,
                format=P6MappingFormat.XER_PROJECT,
                values={"ev": "NaN"},
            )
        )
