from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.reporting import (
    AuthoritativeReportDataset,
    ReportColumn,
    ReportDataType,
    ReportDatasetError,
)


def dataset(**overrides):
    values = dict(
        report_id="schedule-status",
        tenant_id="tenant-1",
        project_id="project-1",
        source_revision=7,
        columns=(
            ReportColumn("activity_id", ReportDataType.STRING, nullable=False),
            ReportColumn("progress", ReportDataType.DECIMAL, nullable=False),
            ReportColumn("start_date", ReportDataType.DATE, nullable=False),
            ReportColumn("duration", ReportDataType.DURATION, nullable=False, duration_unit="day"),
            ReportColumn("active", ReportDataType.BOOLEAN, nullable=False),
        ),
        rows=(
            {
                "activity_id": "A-1",
                "progress": Decimal("42.50"),
                "start_date": datetime(2026, 9, 27, tzinfo=timezone.utc).date(),
                "duration": Decimal("5.0"),
                "active": True,
            },
        ),
        generated_at=datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc),
    )
    values.update(overrides)
    return AuthoritativeReportDataset(**values)


def test_typed_dataset_accepts_distinct_excel_ready_value_types():
    report = dataset()
    report.validate()

    row = report.typed_records()[0]
    assert isinstance(row["progress"], Decimal)
    assert isinstance(row["start_date"].year, int)
    assert isinstance(row["duration"], Decimal)
    assert isinstance(row["active"], bool)


def test_decimal_column_rejects_float():
    report = dataset(
        rows=(
            {
                "activity_id": "A-1",
                "progress": 42.5,
                "start_date": datetime(2026, 9, 27).date(),
                "duration": Decimal("5"),
                "active": True,
            },
        )
    )
    with pytest.raises(ReportDatasetError, match="INVALID_REPORT_VALUE_TYPE:progress"):
        report.validate()


def test_duration_requires_explicit_unit_and_non_negative_decimal():
    with pytest.raises(ReportDatasetError, match="INVALID_REPORT_DURATION_UNIT"):
        ReportColumn("duration", ReportDataType.DURATION).validate()

    report = dataset(
        rows=(
            {
                "activity_id": "A-1",
                "progress": Decimal("42.5"),
                "start_date": datetime(2026, 9, 27).date(),
                "duration": Decimal("-1"),
                "active": True,
            },
        )
    )
    with pytest.raises(ReportDatasetError, match="INVALID_REPORT_DURATION:duration"):
        report.validate()


def test_rows_must_match_declared_columns_exactly():
    report = dataset(
        rows=(
            {
                "activity_id": "A-1",
                "progress": Decimal("42.5"),
                "start_date": datetime(2026, 9, 27).date(),
                "duration": Decimal("5"),
                "active": True,
                "extra": "not-allowed",
            },
        )
    )
    with pytest.raises(ReportDatasetError, match="REPORT_ROW_COLUMNS_MISMATCH"):
        report.validate()


def test_non_data_value_and_naive_datetime_are_rejected():
    report = dataset(
        rows=(
            {
                "activity_id": lambda: "A-1",
                "progress": Decimal("42.5"),
                "start_date": datetime(2026, 9, 27).date(),
                "duration": Decimal("5"),
                "active": True,
            },
        )
    )
    with pytest.raises(ReportDatasetError, match="NON_DATA_REPORT_VALUE:activity_id"):
        report.validate()

    report = dataset(generated_at=datetime(2026, 9, 27, 6, 0))
    with pytest.raises(ReportDatasetError, match="REPORT_GENERATED_AT_MUST_BE_TIMEZONE_AWARE"):
        report.validate()
