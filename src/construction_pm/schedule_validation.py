from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
from typing import Any, Mapping, Sequence

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_xer_codec import P6XerCodec, P6XerCodecError


class ScheduleValidationError(ValueError):
    """Raised when source XER or normalized schedule results are invalid."""


class ComparisonStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    ONLY_SOURCE = "ONLY_SOURCE"
    ONLY_CUBI = "ONLY_CUBI"


@dataclass(frozen=True)
class ScheduleComparisonEntry:
    activity_id: str
    field_name: str
    source_value: str | None
    cubi_value: str | None
    status: ComparisonStatus
    delta_hours: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "activity_id": self.activity_id,
            "field_name": self.field_name,
            "source_value": self.source_value,
            "cubi_value": self.cubi_value,
            "status": self.status.value,
            "delta_hours": self.delta_hours,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ScheduleComparisonReport:
    source_sha256: str
    source_activity_count: int
    cubi_activity_count: int
    matched_activity_count: int
    match_count: int
    mismatch_count: int
    not_comparable_count: int
    missing_in_cubi_count: int
    missing_in_source_count: int
    entries: tuple[ScheduleComparisonEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report without Decimal/date objects."""
        return {
            "contract_version": "schedule-validation-report.v1",
            "source_sha256": self.source_sha256,
            "source_activity_count": self.source_activity_count,
            "cubi_activity_count": self.cubi_activity_count,
            "matched_activity_count": self.matched_activity_count,
            "match_count": self.match_count,
            "mismatch_count": self.mismatch_count,
            "not_comparable_count": self.not_comparable_count,
            "missing_in_cubi_count": self.missing_in_cubi_count,
            "missing_in_source_count": self.missing_in_source_count,
            "entries": [entry.to_dict() for entry in self.entries],
        }


# XER TASK names are used only to read stored source results. The normalized
# CUBI result contract uses explicit names and float values in hours. This
# module does not calculate CPM or infer calendar/unit conversions.
_DATE_FIELDS = (
    ("early_start", "early_start_date"),
    ("early_finish", "early_end_date"),
    ("late_start", "late_start_date"),
    ("late_finish", "late_end_date"),
)
_FLOAT_FIELDS = (
    ("total_float_hours", "total_float_hr_cnt"),
    ("free_float_hours", "free_float_hr_cnt"),
)
_MISSING = object()


def compare_xer_schedule_results(
    source_xer: str | bytes,
    cubi_results: Sequence[Mapping[str, Any]],
    *,
    scope: BackendScope,
    float_tolerance_hours: Decimal = Decimal("0.01"),
) -> ScheduleComparisonReport:
    """Compare stored XER TASK results with normalized CUBI results.

    The caller must execute the authoritative Shared Scheduling Core first and
    supply its output using the normalized names below. Both CUBI float fields
    must already be converted to hours using an explicit, approved calendar/unit
    policy. This function does not perform CPM, calendar arithmetic, resource
    leveling, or unit inference.

    Each CUBI result mapping must contain an activity_id and may contain
    early_start, early_finish, late_start, late_finish, total_float_hours, and
    free_float_hours. Date values may be date, datetime, or ISO-8601 strings.
    Float values must be finite numeric values.
    """
    scope.validate()
    tolerance = _decimal_value(
        float_tolerance_hours, code="INVALID_FLOAT_TOLERANCE"
    )
    if tolerance < 0:
        raise ScheduleValidationError("INVALID_FLOAT_TOLERANCE")
    if not isinstance(source_xer, (str, bytes)):
        raise ScheduleValidationError("INVALID_XER_PAYLOAD")
    if not isinstance(cubi_results, Sequence) or isinstance(cubi_results, (str, bytes)):
        raise ScheduleValidationError("INVALID_CUBI_RESULTS")

    source_bytes = source_xer if isinstance(source_xer, bytes) else source_xer.encode("utf-8")
    source_hash = hashlib.sha256(source_bytes).hexdigest()

    try:
        rows = P6XerCodec().decode(source_xer, scope)
    except P6XerCodecError as exc:
        raise ScheduleValidationError(f"INVALID_XER_DOCUMENT:{exc}") from exc

    source_rows = [
        row for row in rows if row.extensions.get("p6.xer.table") == "TASK"
    ]
    if not source_rows:
        raise ScheduleValidationError("XER_TASK_TABLE_REQUIRED")

    source_activities: dict[str, Mapping[str, Any]] = {}
    for row in source_rows:
        activity_id = row.values.get("task_code")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ScheduleValidationError("XER_TASK_ACTIVITY_ID_REQUIRED")
        activity_id = activity_id.strip()
        if activity_id in source_activities:
            raise ScheduleValidationError(f"DUPLICATE_XER_ACTIVITY_ID:{activity_id}")
        source_activities[activity_id] = row.values

    normalized_cubi: dict[str, Mapping[str, Any]] = {}
    for result in cubi_results:
        if not isinstance(result, Mapping):
            raise ScheduleValidationError("INVALID_CUBI_ACTIVITY_RESULT")
        activity_id = result.get("activity_id")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ScheduleValidationError("CUBI_ACTIVITY_ID_REQUIRED")
        activity_id = activity_id.strip()
        if activity_id in normalized_cubi:
            raise ScheduleValidationError(f"DUPLICATE_CUBI_ACTIVITY_ID:{activity_id}")
        normalized_cubi[activity_id] = result

    entries: list[ScheduleComparisonEntry] = []
    source_ids = set(source_activities)
    cubi_ids = set(normalized_cubi)

    for activity_id in sorted(source_ids - cubi_ids):
        entries.append(
            ScheduleComparisonEntry(
                activity_id=activity_id,
                field_name="activity_identity",
                source_value=activity_id,
                cubi_value=None,
                status=ComparisonStatus.ONLY_SOURCE,
                reason="ACTIVITY_MISSING_FROM_CUBI_RESULT",
            )
        )
    for activity_id in sorted(cubi_ids - source_ids):
        entries.append(
            ScheduleComparisonEntry(
                activity_id=activity_id,
                field_name="activity_identity",
                source_value=None,
                cubi_value=activity_id,
                status=ComparisonStatus.ONLY_CUBI,
                reason="ACTIVITY_NOT_PRESENT_IN_SOURCE_XER",
            )
        )

    for activity_id in sorted(source_ids & cubi_ids):
        source = source_activities[activity_id]
        cubi = normalized_cubi[activity_id]
        for cubi_field, xer_field in _DATE_FIELDS:
            entries.append(
                _compare_field(
                    activity_id=activity_id,
                    field_name=cubi_field,
                    source=source,
                    cubi=cubi,
                    source_field=xer_field,
                    tolerance=tolerance,
                    kind="date",
                )
            )
        for cubi_field, xer_field in _FLOAT_FIELDS:
            entries.append(
                _compare_field(
                    activity_id=activity_id,
                    field_name=cubi_field,
                    source=source,
                    cubi=cubi,
                    source_field=xer_field,
                    tolerance=tolerance,
                    kind="float",
                )
            )

    entries.sort(key=lambda entry: (entry.activity_id, entry.field_name))
    matches = sum(entry.status is ComparisonStatus.MATCH for entry in entries)
    mismatches = sum(entry.status is ComparisonStatus.MISMATCH for entry in entries)
    not_comparable = sum(
        entry.status is ComparisonStatus.NOT_COMPARABLE for entry in entries
    )
    return ScheduleComparisonReport(
        source_sha256=source_hash,
        source_activity_count=len(source_activities),
        cubi_activity_count=len(normalized_cubi),
        matched_activity_count=len(source_ids & cubi_ids),
        match_count=matches,
        mismatch_count=mismatches,
        not_comparable_count=not_comparable,
        missing_in_cubi_count=len(source_ids - cubi_ids),
        missing_in_source_count=len(cubi_ids - source_ids),
        entries=tuple(entries),
    )


def _compare_field(
    *,
    activity_id: str,
    field_name: str,
    source: Mapping[str, Any],
    cubi: Mapping[str, Any],
    source_field: str,
    tolerance: Decimal,
    kind: str,
) -> ScheduleComparisonEntry:
    raw_source = source.get(source_field, _MISSING)
    raw_cubi = cubi.get(field_name, _MISSING)

    if raw_source is _MISSING:
        return ScheduleComparisonEntry(
            activity_id, field_name, None, _report_value(raw_cubi),
            ComparisonStatus.NOT_COMPARABLE, reason="SOURCE_FIELD_ABSENT",
        )
    if raw_source is None or _is_empty_token(raw_source):
        return ScheduleComparisonEntry(
            activity_id, field_name, None, _report_value(raw_cubi),
            ComparisonStatus.NOT_COMPARABLE, reason="SOURCE_VALUE_EMPTY",
        )
    if raw_cubi is _MISSING:
        return ScheduleComparisonEntry(
            activity_id, field_name, _report_value(raw_source), None,
            ComparisonStatus.NOT_COMPARABLE, reason="CUBI_FIELD_ABSENT",
        )
    if raw_cubi is None or _is_empty_token(raw_cubi):
        return ScheduleComparisonEntry(
            activity_id, field_name, _report_value(raw_source), None,
            ComparisonStatus.NOT_COMPARABLE, reason="CUBI_VALUE_EMPTY",
        )

    if kind == "date":
        source_value = _temporal_value(
            raw_source, code="INVALID_XER_DATE", activity_id=activity_id,
            field_name=source_field,
        )
        cubi_value = _temporal_value(
            raw_cubi, code="INVALID_CUBI_DATE", activity_id=activity_id,
            field_name=field_name,
        )
        if not _temporal_precision_compatible(source_value, cubi_value):
            return ScheduleComparisonEntry(
                activity_id, field_name, _report_value(source_value),
                _report_value(cubi_value), ComparisonStatus.NOT_COMPARABLE,
                reason="DATE_PRECISION_OR_TIMEZONE_CONTEXT_MISMATCH",
            )
        status = (
            ComparisonStatus.MATCH
            if _temporal_equal(source_value, cubi_value)
            else ComparisonStatus.MISMATCH
        )
        return ScheduleComparisonEntry(
            activity_id, field_name, _report_value(source_value),
            _report_value(cubi_value), status,
        )

    source_value = _decimal_value(
        raw_source, code="INVALID_XER_FLOAT", activity_id=activity_id,
        field_name=source_field,
    )
    cubi_value = _decimal_value(
        raw_cubi, code="INVALID_CUBI_FLOAT", activity_id=activity_id,
        field_name=field_name,
    )
    delta = cubi_value - source_value
    return ScheduleComparisonEntry(
        activity_id=activity_id,
        field_name=field_name,
        source_value=str(source_value),
        cubi_value=str(cubi_value),
        status=(
            ComparisonStatus.MATCH
            if abs(delta) <= tolerance
            else ComparisonStatus.MISMATCH
        ),
        delta_hours=str(delta),
    )


def _is_empty_token(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() in {"", "NULL"}


def _temporal_value(
    value: Any, *, code: str, activity_id: str, field_name: str
) -> date | datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ScheduleValidationError(f"{code}:{activity_id}:{field_name}")
    text = value.strip()
    if not text or text.upper() == "NULL":
        raise ScheduleValidationError(f"{code}:{activity_id}:{field_name}")
    try:
        if "T" in text or " " in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ScheduleValidationError(
            f"{code}:{activity_id}:{field_name}"
        ) from exc


def _temporal_precision_compatible(
    source: date | datetime, cubi: date | datetime
) -> bool:
    if isinstance(source, datetime) != isinstance(cubi, datetime):
        return False
    if isinstance(source, datetime) and isinstance(cubi, datetime):
        source_aware = source.tzinfo is not None and source.utcoffset() is not None
        cubi_aware = cubi.tzinfo is not None and cubi.utcoffset() is not None
        return source_aware == cubi_aware
    return True


def _temporal_equal(source: date | datetime, cubi: date | datetime) -> bool:
    if isinstance(source, datetime) and isinstance(cubi, datetime):
        if source.tzinfo is not None and source.utcoffset() is not None:
            source = source.astimezone(timezone.utc)
        if cubi.tzinfo is not None and cubi.utcoffset() is not None:
            cubi = cubi.astimezone(timezone.utc)
    return source == cubi


def _decimal_value(value: Any, *, code: str, **context: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ScheduleValidationError(_contextual_code(code, context))
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ScheduleValidationError(_contextual_code(code, context)) from exc
    if not result.is_finite():
        raise ScheduleValidationError(_contextual_code(code, context))
    return result


def _contextual_code(code: str, context: Mapping[str, str]) -> str:
    suffix = ":".join(
        str(context[key]) for key in ("activity_id", "field_name") if key in context
    )
    return f"{code}:{suffix}" if suffix else code


def _report_value(value: Any) -> str | None:
    if value is _MISSING or value is None or _is_empty_token(value):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


__all__ = [
    "ComparisonStatus",
    "ScheduleComparisonEntry",
    "ScheduleComparisonReport",
    "ScheduleValidationError",
    "compare_xer_schedule_results",
]
