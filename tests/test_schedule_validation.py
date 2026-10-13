from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.schedule_validation import (
    ComparisonStatus,
    ScheduleValidationError,
    compare_xer_schedule_results,
)


def scope() -> BackendScope:
    return BackendScope(
        tenant_id="tenant-test",
        project_id="validation-run-1",
        project_revision=0,
    )


def xer_document(
    rows: tuple[tuple[str, ...], ...] = (
        (
            "DAM-010",
            "1010",
            "2026-01-05 08:00",
            "2026-01-06 17:00",
            "2026-01-07 08:00",
            "2026-01-08 17:00",
            "8.00",
            "4.00",
        ),
    ),
    fields: tuple[str, ...] = (
        "task_code",
        "task_id",
        "early_start_date",
        "early_end_date",
        "late_start_date",
        "late_end_date",
        "total_float_hr_cnt",
        "free_float_hr_cnt",
    ),
) -> str:
    result = ["%T\tTASK", "%F\t" + "\t".join(fields)]
    result.extend("%R\t" + "\t".join(row) for row in rows)
    result.append("%E")
    return "\n".join(result) + "\n"


def cubi_result(**overrides):
    result = {
        "activity_id": "DAM-010",
        "early_start": datetime(2026, 1, 5, 8, 0),
        "early_finish": datetime(2026, 1, 6, 17, 0),
        "late_start": datetime(2026, 1, 7, 8, 0),
        "late_finish": datetime(2026, 1, 8, 17, 0),
        "total_float_hours": Decimal("8.00"),
        "free_float_hours": Decimal("4.00"),
    }
    result.update(overrides)
    return result


def test_identical_schedule_result_values_report_all_matches_and_json_output():
    source = xer_document()

    report = compare_xer_schedule_results(
        source, [cubi_result()], scope=scope()
    )

    assert report.source_activity_count == 1
    assert report.cubi_activity_count == 1
    assert report.matched_activity_count == 1
    assert report.match_count == 6
    assert report.mismatch_count == 0
    assert report.not_comparable_count == 0
    assert report.missing_in_cubi_count == 0
    assert report.missing_in_source_count == 0
    assert all(entry.status is ComparisonStatus.MATCH for entry in report.entries)
    assert len(report.source_sha256) == 64
    serialized = json.dumps(report.to_dict(), sort_keys=True)
    assert '"contract_version": "schedule-validation-report.v1"' in serialized


def test_date_and_float_differences_are_reported_with_activity_and_field():
    report = compare_xer_schedule_results(
        xer_document(),
        [
            cubi_result(
                early_start=datetime(2026, 1, 6, 8, 0),
                total_float_hours=Decimal("8.5"),
            )
        ],
        scope=scope(),
        float_tolerance_hours=Decimal("0.01"),
    )

    by_field = {entry.field_name: entry for entry in report.entries}
    assert by_field["early_start"].status is ComparisonStatus.MISMATCH
    assert by_field["early_start"].activity_id == "DAM-010"
    assert by_field["total_float_hours"].status is ComparisonStatus.MISMATCH
    assert by_field["total_float_hours"].delta_hours == "0.5"
    assert report.mismatch_count == 2


def test_float_delta_inside_explicit_tolerance_is_a_match():
    report = compare_xer_schedule_results(
        xer_document(),
        [cubi_result(total_float_hours=Decimal("8.009"))],
        scope=scope(),
        float_tolerance_hours=Decimal("0.01"),
    )

    total_float = next(
        entry for entry in report.entries if entry.field_name == "total_float_hours"
    )
    assert total_float.status is ComparisonStatus.MATCH
    assert total_float.delta_hours == "0.009"


def test_source_and_cubi_activity_identity_gaps_are_reported_not_silently_ignored():
    report = compare_xer_schedule_results(
        xer_document(),
        [{"activity_id": "DAM-020"}],
        scope=scope(),
    )

    assert report.missing_in_cubi_count == 1
    assert report.missing_in_source_count == 1
    assert [(entry.activity_id, entry.status) for entry in report.entries] == [
        ("DAM-010", ComparisonStatus.ONLY_SOURCE),
        ("DAM-020", ComparisonStatus.ONLY_CUBI),
    ]


def test_missing_source_fields_are_not_comparable_instead_of_being_assumed_equal():
    source = xer_document(
        rows=(("DAM-010", "1010"),),
        fields=("task_code", "task_id"),
    )

    report = compare_xer_schedule_results(
        source, [{"activity_id": "DAM-010"}], scope=scope()
    )

    assert report.match_count == 0
    assert report.mismatch_count == 0
    assert report.not_comparable_count == 6
    assert all(
        entry.status is ComparisonStatus.NOT_COMPARABLE for entry in report.entries
    )
    assert all(entry.reason == "SOURCE_FIELD_ABSENT" for entry in report.entries)


def test_date_only_and_datetime_values_are_not_compared_at_different_precision():
    report = compare_xer_schedule_results(
        xer_document(),
        [cubi_result(early_start=date(2026, 1, 5))],
        scope=scope(),
    )

    early_start = next(
        entry for entry in report.entries if entry.field_name == "early_start"
    )
    assert early_start.status is ComparisonStatus.NOT_COMPARABLE
    assert early_start.reason == "DATE_PRECISION_OR_TIMEZONE_CONTEXT_MISMATCH"


def test_duplicate_source_activity_ids_are_rejected():
    source = xer_document(
        rows=(
            ("DAM-010", "1010", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "8", "4"),
            ("DAM-010", "1011", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "8", "4"),
        )
    )

    with pytest.raises(ScheduleValidationError, match="DUPLICATE_XER_ACTIVITY_ID:DAM-010"):
        compare_xer_schedule_results(source, [], scope=scope())


def test_duplicate_cubi_activity_ids_are_rejected():
    with pytest.raises(ScheduleValidationError, match="DUPLICATE_CUBI_ACTIVITY_ID:DAM-010"):
        compare_xer_schedule_results(
            xer_document(), [cubi_result(), cubi_result()], scope=scope()
        )


def test_corrupt_xer_is_rejected_with_parser_evidence():
    with pytest.raises(ScheduleValidationError, match="INVALID_XER_DOCUMENT"):
        compare_xer_schedule_results(
            "%T\tTASK\n%F\ttask_code\ttask_id\n%R\tDAM-010\n%E\n",
            [],
            scope=scope(),
        )


def test_xer_without_task_table_is_rejected():
    with pytest.raises(ScheduleValidationError, match="XER_TASK_TABLE_REQUIRED"):
        compare_xer_schedule_results(
            "%T\tPROJECT\n%F\tproj_id\n%R\tP-1\n%E\n",
            [],
            scope=scope(),
        )


def test_invalid_cubi_float_is_rejected_not_coerced():
    with pytest.raises(ScheduleValidationError, match="INVALID_CUBI_FLOAT:DAM-010:total_float_hours"):
        compare_xer_schedule_results(
            xer_document(),
            [cubi_result(total_float_hours=True)],
            scope=scope(),
        )

def test_report_matches_versioned_shared_json_contract_shape():
    contract_path = (
        Path(__file__).parents[1]
        / "shared"
        / "contracts"
        / "schedule-validation-report.v1.schema.json"
    )
    schema = json.loads(contract_path.read_text(encoding="utf-8"))
    report = compare_xer_schedule_results(
        xer_document(), [cubi_result()], scope=scope()
    ).to_dict()

    assert report["contract_version"] == schema["properties"]["contract_version"]["const"]
    assert set(report) == set(schema["required"])
    entry_contract = schema["properties"]["entries"]["items"]
    assert all(set(entry) == set(entry_contract["required"]) for entry in report["entries"])
    assert all(
        entry["status"] in entry_contract["properties"]["status"]["enum"]
        for entry in report["entries"]
    )

