from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Protocol


class ReportDatasetError(ValueError):
    """Raised when a reporting dataset violates its typed contract."""


class ReportDataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    DURATION = "duration"
    BOOLEAN = "boolean"


@dataclass(frozen=True)
class ReportColumn:
    key: str
    data_type: ReportDataType
    nullable: bool = True
    duration_unit: str | None = None

    def validate(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ReportDatasetError("INVALID_REPORT_COLUMN_KEY")
        if not isinstance(self.data_type, ReportDataType):
            raise ReportDatasetError("INVALID_REPORT_COLUMN_TYPE")
        if self.data_type is ReportDataType.DURATION:
            if self.duration_unit not in {"day", "hour", "minute"}:
                raise ReportDatasetError("INVALID_REPORT_DURATION_UNIT")
        elif self.duration_unit is not None:
            raise ReportDatasetError("UNEXPECTED_REPORT_DURATION_UNIT")


@dataclass(frozen=True)
class AuthoritativeReportDataset:
    """Read-only report data supplied by an authoritative domain/query source.

    This boundary validates transportable values only. It performs no
    Scheduling/P6, Progress/EVM, Resource/Cost, financial, or other domain
    calculations.
    """

    report_id: str
    tenant_id: str
    project_id: str
    source_revision: int
    columns: tuple[ReportColumn, ...]
    rows: tuple[Mapping[str, Any], ...] = ()
    generated_at: datetime | None = None

    def validate(self) -> None:
        for name, value in (
            ("report_id", self.report_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ReportDatasetError(f"INVALID_{name.upper()}")
        if (
            isinstance(self.source_revision, bool)
            or not isinstance(self.source_revision, int)
            or self.source_revision < 0
        ):
            raise ReportDatasetError("INVALID_REPORT_SOURCE_REVISION")
        if len({column.key for column in self.columns}) != len(self.columns):
            raise ReportDatasetError("DUPLICATE_REPORT_COLUMN")
        for column in self.columns:
            column.validate()
        if self.generated_at is not None:
            if not isinstance(self.generated_at, datetime):
                raise ReportDatasetError("INVALID_REPORT_GENERATED_AT")
            if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
                raise ReportDatasetError("REPORT_GENERATED_AT_MUST_BE_TIMEZONE_AWARE")

        column_by_key = {column.key: column for column in self.columns}
        for row in self.rows:
            if not isinstance(row, Mapping):
                raise ReportDatasetError("INVALID_REPORT_ROW")
            if set(row) != set(column_by_key):
                raise ReportDatasetError("REPORT_ROW_COLUMNS_MISMATCH")
            for key, value in row.items():
                self._validate_value(column_by_key[key], value)

    @staticmethod
    def _validate_value(column: ReportColumn, value: Any) -> None:
        if value is None:
            if column.nullable:
                return
            raise ReportDatasetError(f"NULL_REPORT_VALUE:{column.key}")

        if callable(value):
            raise ReportDatasetError(f"NON_DATA_REPORT_VALUE:{column.key}")

        valid = {
            ReportDataType.STRING: isinstance(value, str),
            ReportDataType.INTEGER: isinstance(value, int) and not isinstance(value, bool),
            ReportDataType.DECIMAL: isinstance(value, Decimal),
            ReportDataType.DATE: isinstance(value, date) and not isinstance(value, datetime),
            ReportDataType.DATETIME: isinstance(value, datetime),
            ReportDataType.DURATION: isinstance(value, Decimal),
            ReportDataType.BOOLEAN: isinstance(value, bool),
        }[column.data_type]
        if not valid:
            raise ReportDatasetError(f"INVALID_REPORT_VALUE_TYPE:{column.key}")

        if column.data_type is ReportDataType.DECIMAL and not value.is_finite():
            raise ReportDatasetError(f"INVALID_REPORT_DECIMAL:{column.key}")
        if column.data_type is ReportDataType.DURATION and (
            not value.is_finite() or value < 0
        ):
            raise ReportDatasetError(f"INVALID_REPORT_DURATION:{column.key}")
        if column.data_type is ReportDataType.DATETIME:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ReportDatasetError(f"REPORT_DATETIME_MUST_BE_TIMEZONE_AWARE:{column.key}")

    def typed_records(self) -> tuple[Mapping[str, Any], ...]:
        self.validate()
        return tuple(dict(row) for row in self.rows)


class ReportQueryProvider(Protocol):
    """Application boundary for querying authoritative calculated datasets."""

    def query(self, report_id: str, tenant_id: str, project_id: str) -> AuthoritativeReportDataset:
        ...
