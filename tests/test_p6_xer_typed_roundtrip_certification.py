from datetime import date
from decimal import Decimal

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)
from construction_pm.p6_xer_codec import P6XerCodec


def test_xer_round_trip_preserves_canonical_date_and_decimal_precision() -> None:
    scope = BackendScope(tenant_id="t1", project_id="p1", project_revision=4)
    mappings = (
        PersistedP6Mapping(
            scope=scope,
            definition=P6MappingDefinition(
                mapping_id="activity.planned_start",
                registry_version="p6-field-registry.v1",
                format=P6MappingFormat.XER_PROJECT,
                subject_area="Activity",
                source_field="target_start_date",
                canonical_field="activity.planned_start",
                status=P6MappingStatus.SUPPORTED,
                source_type="date",
                canonical_type="date",
            ),
        ),
        PersistedP6Mapping(
            scope=scope,
            definition=P6MappingDefinition(
                mapping_id="activity.earned_value_cost",
                registry_version="p6-field-registry.v1",
                format=P6MappingFormat.XER_PROJECT,
                subject_area="Activity",
                source_field="target_cost",
                canonical_field="activity.earned_value_cost",
                status=P6MappingStatus.SUPPORTED,
                source_type="decimal",
                canonical_type="double",
            ),
        ),
    )
    adapter = P6InterchangeAdapter(
        mapper=P6InterchangeMapper(mappings),
        codec=P6XerCodec(),
    )

    exported = adapter.export_document(
        [{
            "activity.planned_start": date(2026, 10, 5),
            "activity.earned_value_cost": Decimal("1234567890.123400"),
        }],
        scope=scope,
        extensions=[{"p6.xer.table": "TASK"}],
    )
    imported = adapter.import_document(exported, scope=scope)

    assert imported[0].values == {
        "activity.planned_start": date(2026, 10, 5),
        "activity.earned_value_cost": Decimal("1234567890.123400"),
    }
