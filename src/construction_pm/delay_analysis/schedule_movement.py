from __future__ import annotations

"""Read-only movement assessment over two authoritative P6 schedule runs.

This module compares already-calculated scheduler outputs. It does not run CPM,
recalculate float, establish causation, or determine contractual delay.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping

from ..scheduling.schedule import ScheduleResult


class ScheduleMovementAnalysisError(ValueError):
    """Raised when schedule movement evidence is incomplete or inconsistent."""


def _require_sha256(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ScheduleMovementAnalysisError(f"INVALID_{field_name.upper()}")


@dataclass(frozen=True)
class ScheduleRunReference:
    """Immutable provenance for one authoritative, already-calculated schedule run."""

    tenant_id: str
    project_id: str
    project_revision: int
    snapshot_id: str
    snapshot_hash: str
    calculation_identity: str
    data_date: date
    engine_version: str
    calendar_context_hash: str
    scheduling_settings_hash: str
    schedule_log_hash: str

    def validate(self) -> None:
        for field_name, value in (
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("snapshot_id", self.snapshot_id),
            ("engine_version", self.engine_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ScheduleMovementAnalysisError(f"INVALID_{field_name.upper()}")
        if (
            isinstance(self.project_revision, bool)
            or not isinstance(self.project_revision, int)
            or self.project_revision < 0
        ):
            raise ScheduleMovementAnalysisError("INVALID_PROJECT_REVISION")
        if not isinstance(self.data_date, date) or isinstance(self.data_date, datetime):
            raise ScheduleMovementAnalysisError("INVALID_DATA_DATE")
        _require_sha256(self.snapshot_hash, "snapshot_hash")
        _require_sha256(self.calculation_identity, "calculation_identity")
        _require_sha256(self.calendar_context_hash, "calendar_context_hash")
        _require_sha256(self.scheduling_settings_hash, "scheduling_settings_hash")
        _require_sha256(self.schedule_log_hash, "schedule_log_hash")


@dataclass(frozen=True)
class ActivityScheduleMovement:
    activity_id: str
    baseline_early_start: date
    current_early_start: date
    early_start_delta_calendar_days: int
    baseline_early_finish: date
    current_early_finish: date
    early_finish_delta_calendar_days: int
    baseline_total_float: int
    current_total_float: int
    total_float_delta_native_units: int
    baseline_free_float: int
    current_free_float: int
    free_float_delta_native_units: int
    baseline_critical: bool
    current_critical: bool
    criticality_changed: bool
    baseline_float_path: int | None
    current_float_path: int | None


@dataclass(frozen=True)
class ScheduleMovementAssessment:
    """Deterministic comparison facts; not a forensic delay opinion."""

    baseline: ScheduleRunReference
    current: ScheduleRunReference
    baseline_project_finish: date
    current_project_finish: date
    project_finish_delta_calendar_days: int
    added_activity_ids: tuple[str, ...]
    removed_activity_ids: tuple[str, ...]
    activity_movements: tuple[ActivityScheduleMovement, ...]
    analysis_hash: str
    method: str = "P6_AUTHORITATIVE_SCHEDULE_MOVEMENT"
    limitations: tuple[str, ...] = (
        "Calendar-day date movement is not working-day delay.",
        "Scheduler-native float units are reported without recalculation or conversion.",
        "Movement and criticality changes do not establish causation, concurrency, responsibility, entitlement, EOT, damages, or cost.",
        "This comparison is not Time Impact Analysis and does not model an inserted fragnet or event.",
        "Results are only as complete as the two immutable schedule inputs and their recorded settings/log provenance.",
    )


def _canonical_assessment_payload(
    baseline: ScheduleRunReference,
    current: ScheduleRunReference,
    baseline_finish: date,
    current_finish: date,
    added: tuple[str, ...],
    removed: tuple[str, ...],
    movements: tuple[ActivityScheduleMovement, ...],
) -> str:
    def ref_payload(ref: ScheduleRunReference) -> dict[str, object]:
        return {
            "tenant_id": ref.tenant_id,
            "project_id": ref.project_id,
            "project_revision": ref.project_revision,
            "snapshot_id": ref.snapshot_id,
            "snapshot_hash": ref.snapshot_hash,
            "calculation_identity": ref.calculation_identity,
            "data_date": ref.data_date.isoformat(),
            "engine_version": ref.engine_version,
            "calendar_context_hash": ref.calendar_context_hash,
            "scheduling_settings_hash": ref.scheduling_settings_hash,
            "schedule_log_hash": ref.schedule_log_hash,
        }

    return json.dumps(
        {
            "method": "P6_AUTHORITATIVE_SCHEDULE_MOVEMENT",
            "baseline": ref_payload(baseline),
            "current": ref_payload(current),
            "baseline_project_finish": baseline_finish.isoformat(),
            "current_project_finish": current_finish.isoformat(),
            "project_finish_delta_calendar_days": (current_finish - baseline_finish).days,
            "added_activity_ids": list(added),
            "removed_activity_ids": list(removed),
            "activity_movements": [
                {
                    "activity_id": item.activity_id,
                    "baseline_early_start": item.baseline_early_start.isoformat(),
                    "current_early_start": item.current_early_start.isoformat(),
                    "early_start_delta_calendar_days": item.early_start_delta_calendar_days,
                    "baseline_early_finish": item.baseline_early_finish.isoformat(),
                    "current_early_finish": item.current_early_finish.isoformat(),
                    "early_finish_delta_calendar_days": item.early_finish_delta_calendar_days,
                    "baseline_total_float": item.baseline_total_float,
                    "current_total_float": item.current_total_float,
                    "total_float_delta_native_units": item.total_float_delta_native_units,
                    "baseline_free_float": item.baseline_free_float,
                    "current_free_float": item.current_free_float,
                    "free_float_delta_native_units": item.free_float_delta_native_units,
                    "baseline_critical": item.baseline_critical,
                    "current_critical": item.current_critical,
                    "criticality_changed": item.criticality_changed,
                    "baseline_float_path": item.baseline_float_path,
                    "current_float_path": item.current_float_path,
                }
                for item in movements
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def assess_schedule_movement(
    baseline_reference: ScheduleRunReference,
    baseline_result: ScheduleResult,
    current_reference: ScheduleRunReference,
    current_result: ScheduleResult,
) -> ScheduleMovementAssessment:
    """Compare two authoritative ScheduleResult objects without recalculating CPM.

    The caller must obtain both references and results from trusted, immutable
    server-side records. Client-supplied identity/provenance is not an
    authorization boundary.
    """
    baseline_reference.validate()
    current_reference.validate()

    if baseline_reference.tenant_id != current_reference.tenant_id:
        raise ScheduleMovementAnalysisError("TENANT_SCOPE_MISMATCH")
    if baseline_reference.project_id != current_reference.project_id:
        raise ScheduleMovementAnalysisError("PROJECT_SCOPE_MISMATCH")
    if current_reference.project_revision < baseline_reference.project_revision:
        raise ScheduleMovementAnalysisError("STALE_CURRENT_PROJECT_REVISION")
    if current_reference.data_date < baseline_reference.data_date:
        raise ScheduleMovementAnalysisError("CURRENT_DATA_DATE_PRECEDES_BASELINE")
    if (
        baseline_reference.snapshot_hash == current_reference.snapshot_hash
        and baseline_reference.calculation_identity == current_reference.calculation_identity
    ):
        raise ScheduleMovementAnalysisError("IDENTICAL_INPUT_SNAPSHOTS")
    if baseline_result.mode != current_result.mode:
        raise ScheduleMovementAnalysisError("SCHEDULE_MODE_MISMATCH")
    if not isinstance(baseline_result.floats, Mapping) or not baseline_result.floats:
        raise ScheduleMovementAnalysisError("BASELINE_SCHEDULER_OUTPUTS_MISSING")
    if not isinstance(current_result.floats, Mapping) or not current_result.floats:
        raise ScheduleMovementAnalysisError("CURRENT_SCHEDULER_OUTPUTS_MISSING")

    baseline_ids = set(baseline_result.floats)
    current_ids = set(current_result.floats)
    common_ids = sorted(baseline_ids & current_ids)
    added = tuple(sorted(current_ids - baseline_ids))
    removed = tuple(sorted(baseline_ids - current_ids))

    movements: list[ActivityScheduleMovement] = []
    for activity_id in common_ids:
        before = baseline_result.floats[activity_id]
        after = current_result.floats[activity_id]
        movements.append(
            ActivityScheduleMovement(
                activity_id=activity_id,
                baseline_early_start=before.early_start,
                current_early_start=after.early_start,
                early_start_delta_calendar_days=(after.early_start - before.early_start).days,
                baseline_early_finish=before.early_finish,
                current_early_finish=after.early_finish,
                early_finish_delta_calendar_days=(after.early_finish - before.early_finish).days,
                baseline_total_float=before.total_float,
                current_total_float=after.total_float,
                total_float_delta_native_units=after.total_float - before.total_float,
                baseline_free_float=before.free_float,
                current_free_float=after.free_float,
                free_float_delta_native_units=after.free_float - before.free_float,
                baseline_critical=before.critical,
                current_critical=after.critical,
                criticality_changed=before.critical != after.critical,
                baseline_float_path=before.float_path,
                current_float_path=after.float_path,
            )
        )

    movements_tuple = tuple(movements)
    payload = _canonical_assessment_payload(
        baseline_reference,
        current_reference,
        baseline_result.project_finish,
        current_result.project_finish,
        added,
        removed,
        movements_tuple,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return ScheduleMovementAssessment(
        baseline=baseline_reference,
        current=current_reference,
        baseline_project_finish=baseline_result.project_finish,
        current_project_finish=current_result.project_finish,
        project_finish_delta_calendar_days=(
            current_result.project_finish - baseline_result.project_finish
        ).days,
        added_activity_ids=added,
        removed_activity_ids=removed,
        activity_movements=movements_tuple,
        analysis_hash=digest,
    )
