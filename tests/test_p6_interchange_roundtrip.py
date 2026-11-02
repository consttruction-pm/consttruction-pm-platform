from datetime import date
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_interchange_adapter import P6InterchangeAdapter
from construction_pm.p6_interchange_mapping import P6InterchangeMapper
from construction_pm.p6_interchange_verification import (
    P6InterchangeVerificationError,
    verify_round_trip,
    verify_round_trips,
)
from construction_pm.p6_mapping_registry import (
    P6MappingDefinition,
    P6MappingFormat,
    P6MappingStatus,
    PersistedP6Mapping,
)
from construction_pm.p6_mpx_codec import P6MpxCodec, P6MpxCodecError
from construction_pm.p6_msproject_xml_codec import P6MsProjectXmlCodec
from construction_pm.p6_primavera_xml_codec import P6PrimaveraXmlCodec
from construction_pm.p6_xer_codec import P6XerCodec
from construction_pm.p6_xls_codec import P6XlsCodec
from construction_pm.p6_xlsx_codec import P6XlsxCodec


def scope() -> BackendScope:
    return BackendScope(tenant_id="t1", project_id="p1", project_revision=4)


_CASES = {
    P6MappingFormat.XER_PROJECT: (
        P6XerCodec(),
        {"p6.xer.table": "TASK"},
        ("task_id", "target_start_date", "target_cost", "calendar_id", "active", "target_end_date"),
    ),
    P6MappingFormat.PRIMAVERA_XML: (
        P6PrimaveraXmlCodec(),
        {"p6.primavera.xml.object": "Activity"},
        ("Id", "StartDate", "Cost", "CalendarObjectId", "Active", "FinishDate"),
    ),
    P6MappingFormat.MSPROJECT_XML: (
        P6MsProjectXmlCodec(),
        {
            "p6.msproject.xml.collection": "Tasks",
            "p6.msproject.xml.object": "Task",
        },
        ("UID", "Start", "Cost", "CalendarUID", "Active", "Finish"),
    ),
    P6MappingFormat.XLS: (
        P6XlsCodec(),
        {"p6.xls.sheet": "Activities"},
        ("Activity ID", "Start", "Cost", "Calendar", "Active", "Finish"),
    ),
    P6MappingFormat.XLSX: (
        P6XlsxCodec(),
        {"p6.xlsx.sheet": "Activities"},
        ("Activity ID", "Start", "Cost", "Calendar", "Active", "Finish"),
    ),
    P6MappingFormat.MPX: (
        P6MpxCodec(),
        {
            "p6.mpx.record": "TASK",
            "p6.mpx.separator": ",",
            "p6.mpx.file_creation": ("Microsoft Project", "4.0", "850"),
        },
        ("ID", "Start", "Cost", "Calendar", "Active", "Finish"),
    ),
}

_CANONICAL = (
    ("activity.activity_id", "string"),
    ("activity.planned_start", "date"),
    ("activity.earned_value_cost", "double"),
    ("activity.calendar_object_id", "integer"),
    ("schedule_options.calculate_float_based_on_finish_date", "boolean"),
    ("activity.planned_finish", "date"),
)


def _adapter(format: P6MappingFormat) -> P6InterchangeAdapter:
    _, _, sources = _CASES[format]
    mappings = tuple(
        PersistedP6Mapping(
            scope=scope(),
            definition=P6MappingDefinition(
                mapping_id=f"{format.value}.{canonical}",
                registry_version="p6-field-registry.v1",
                format=format,
                subject_area="Activity",
                source_field=source,
                canonical_field=canonical,
                status=P6MappingStatus.SUPPORTED,
                canonical_type=canonical_type,
            ),
        )
        for (canonical, canonical_type), source in zip(_CANONICAL, sources)
    )
    return P6InterchangeAdapter(
        mapper=P6InterchangeMapper(mappings),
        codec=_CASES[format][0],
    )


def _values(format: P6MappingFormat) -> dict[str, object]:
    return {
        "activity.activity_id": "A-10",
        "activity.planned_start": date(2026, 11, 2),
        "activity.earned_value_cost": Decimal("1234.5"),
        "activity.calendar_object_id": 42,
        "schedule_options.calculate_float_based_on_finish_date": True,
        "activity.planned_finish": None,
    }


@pytest.mark.parametrize("format", tuple(_CASES))
def test_round_trip_preserves_typed_canonical_values_and_nulls(format):
    report = verify_round_trip(
        _adapter(format),
        scope=scope(),
        values=_values(format),
        extensions=_CASES[format][1],
    )

    assert report.canonical_lossless, report.to_payload()
    assert report.mismatched_fields == ()
    assert report.output_values["activity.activity_id"] == "A-10"
    assert report.output_values["activity.planned_start"] == date(2026, 11, 2)
    assert report.output_values["activity.earned_value_cost"] == Decimal("1234.5")
    assert report.output_values["activity.calendar_object_id"] == 42
    assert (
        report.output_values[
            "schedule_options.calculate_float_based_on_finish_date"
        ]
        is True
    )
    assert report.output_values["activity.planned_finish"] is None


def test_mpX_export_fails_closed_when_a_value_has_no_record_slot():
    # MPX has no generic extension channel, so a vendor field cannot be
    # represented in the file. The exchange must refuse it rather than drop it
    # and later claim a lossless round trip.
    adapter = _adapter(P6MappingFormat.MPX)
    with pytest.raises(P6MpxCodecError, match="UNREPRESENTABLE_MPX_EXTENSIONS"):
        verify_round_trip(
            adapter,
            scope=scope(),
            values={**_values(P6MappingFormat.MPX), "unmapped": "kept"},
            extensions=_CASES[P6MappingFormat.MPX][1],
        )


@pytest.mark.parametrize("format", tuple(_CASES))
def test_mapper_reports_unknown_import_fields_instead_of_dropping_them(format):
    codec, extensions, sources = _CASES[format]
    adapter = _adapter(format)
    values = {sources[0]: "A-10", "vendor-only": "kept"}
    # Build the provider document directly to inject a field no mapping covers.
    from construction_pm.p6_interchange_mapping import P6InterchangeResult

    document = codec.encode(
        (P6InterchangeResult(dict(values), dict(extensions)),),
        scope(),
    )
    imported = adapter.import_document(document, scope=scope())
    assert imported[0].values == {"activity.activity_id": "A-10"}
    assert "PRESERVED_UNKNOWN_FIELD:vendor-only" in imported[0].warnings
    preserved = {
        key: value
        for key, value in imported[0].extensions.items()
        if key.endswith(".vendor-only")
    }
    assert preserved == {"p6.interchange.t1.p1.vendor-only": "kept"}


def test_multiple_rows_are_verified_in_order():
    reports = verify_round_trips(
        _adapter(P6MappingFormat.XER_PROJECT),
        scope=scope(),
        rows=(
            (
                {**_values(P6MappingFormat.XER_PROJECT), "activity.activity_id": "A-1"},
                {"p6.xer.table": "TASK"},
            ),
            (
                {**_values(P6MappingFormat.XER_PROJECT), "activity.activity_id": "A-2"},
                {"p6.xer.table": "TASK"},
            ),
        ),
    )
    assert [report.output_values["activity.activity_id"] for report in reports] == [
        "A-1",
        "A-2",
    ]
    assert all(report.canonical_lossless for report in reports)


def test_empty_verification_input_fails_closed():
    with pytest.raises(P6InterchangeVerificationError, match="ROUND_TRIP_VALUES_REQUIRED"):
        verify_round_trip(
            _adapter(P6MappingFormat.PRIMAVERA_XML),
            scope=scope(),
            values={},
        )
