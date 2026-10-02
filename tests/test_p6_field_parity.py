import json

from construction_pm.p6_field_parity import compare_field_registry_to_inventory
from construction_pm.p6_field_registry import fields_by_subject


def _registry_records() -> list[dict[str, object]]:
    return [
        {
            "subject_area": field.subject_area,
            "p6_field": field.p6_field,
            "data_type": field.data_type.value,
            "writable": field.writable,
            "computed": field.computed,
            "unit": field.unit,
        }
        for field in fields_by_subject("Activity")
    ]


def test_activity_registry_drift_gate_matches_release_26_inventory_metrics():
    with open(
        "docs/architecture/P6_ACTIVITY_FIELD_INVENTORY_2026-09-28.json",
        encoding="utf-8",
    ) as handle:
        inventory = json.load(handle)

    comparison = compare_field_registry_to_inventory(
        _registry_records(),
        inventory["fields"],
    )

    assert comparison.exact_match_count == 126
    assert comparison.registry_only_count == 9
    assert comparison.inventory_only_count == 150
    assert comparison.is_metadata_consistent


def test_activity_aliases_are_not_counted_as_exact_matches():
    comparison = compare_field_registry_to_inventory(
        [{"subject_area": "Activity", "p6_field": "ActivityId"}],
        [{"subject_area": "Activity", "p6_field": "Id"}],
    )

    assert comparison.exact_matches == ()
    assert comparison.registry_only == (("Activity", "ActivityId"),)
    assert comparison.inventory_only == (("Activity", "Id"),)


def test_populated_inventory_metadata_exposes_registry_drift():
    comparison = compare_field_registry_to_inventory(
        [
            {
                "subject_area": "Activity",
                "p6_field": "PlannedDuration",
                "data_type": "duration",
                "writable": False,
                "computed": True,
                "unit": "working-time",
            }
        ],
        [
            {
                "subject_area": "Activity",
                "p6_field": "PlannedDuration",
                "data_type": "double",
                "writable": False,
                "computed": True,
                "unit": "working-time",
            }
        ],
    )

    assert len(comparison.metadata_mismatches) == 1
    mismatch = comparison.metadata_mismatches[0]
    assert mismatch.key == ("Activity", "PlannedDuration")
    assert mismatch.attribute == "data_type"
    assert mismatch.registry_value == "duration"
    assert mismatch.inventory_value == "double"


def test_duplicate_field_identity_is_rejected():
    fields = [
        {"subject_area": "Activity", "p6_field": "Name"},
        {"subject_area": "Activity", "p6_field": "Name"},
    ]

    try:
        compare_field_registry_to_inventory(fields, [])
    except ValueError as exc:
        assert "duplicate field identity" in str(exc)
    else:
        raise AssertionError("duplicate field identity must be rejected")
