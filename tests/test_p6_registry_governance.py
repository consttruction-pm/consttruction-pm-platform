import pytest

from construction_pm.p6_registry_governance import (
    P6FieldDisposition,
    P6RegistryCertificationError,
    P6RegistryStatus,
    require_certifiable,
    summarize_completeness,
)


def field(field_id: str, disposition: P6FieldDisposition) -> dict[str, object]:
    return {"field_id": field_id, "disposition": disposition.value}


def test_seeded_registry_reports_unknown_coverage_until_reference_count_is_known():
    result = summarize_completeness(
        status=P6RegistryStatus.SEEDED_CORE_CATALOG,
        expected_field_count=None,
        fields=[field("activity.name", P6FieldDisposition.SEEDED_NOT_CERTIFIED)],
    )
    assert result.inventory_coverage_percent is None
    assert result.coverage_percent is None
    assert result.certification_ready is False
    assert result.approved_field_count == 0
    assert result.dispositioned_field_count == 0


def test_certification_requires_every_field_to_have_an_approved_disposition():
    with pytest.raises(P6RegistryCertificationError):
        require_certifiable(
            status=P6RegistryStatus.CERTIFIED,
            expected_field_count=2,
            fields=[
                field("activity.name", P6FieldDisposition.IMPLEMENTED),
                field("activity.bad", P6FieldDisposition.PENDING),
            ],
        )


def test_certification_accepts_implemented_superset_and_explicit_out_of_scope():
    result = require_certifiable(
        status=P6RegistryStatus.CERTIFIED,
        expected_field_count=3,
        fields=[
            field("activity.name", P6FieldDisposition.IMPLEMENTED),
            field("activity.extra", P6FieldDisposition.EQUIVALENT_SUPERSET),
            field("activity.outside", P6FieldDisposition.OUTSIDE_SCOPE),
        ],
    )
    assert result.certification_ready is True
    assert result.inventory_coverage_percent == 100.0
    assert result.coverage_percent == 100.0


def test_duplicate_field_ids_are_rejected():
    with pytest.raises(P6RegistryCertificationError):
        summarize_completeness(
            status=P6RegistryStatus.COMPLETE_CATALOG,
            expected_field_count=2,
            fields=[
                field("activity.name", P6FieldDisposition.IMPLEMENTED),
                field("activity.name", P6FieldDisposition.IMPLEMENTED),
            ],
        )


def test_expected_count_cannot_be_lower_than_inventory_count():
    with pytest.raises(P6RegistryCertificationError):
        summarize_completeness(
            status=P6RegistryStatus.COMPLETE_CATALOG,
            expected_field_count=1,
            fields=[
                field("activity.name", P6FieldDisposition.IMPLEMENTED),
                field("activity.id", P6FieldDisposition.IMPLEMENTED),
            ],
        )
