from __future__ import annotations

"""Authoritative snapshot -> Shared Scheduling Core evaluation boundary."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping

from .schedule_input_snapshot_repository import ScheduleInputSnapshot
from .schedule_snapshot_materializer import MaterializedScheduleInput, materialize_schedule_snapshot
from .scheduling.calendar_context import CalendarResolverRegistry
from .scheduling.calculation_context import CalculationContext
from .scheduling.forward_pass import ScheduledActivity
from .scheduling.leveling_scheduler import schedule_with_resource_leveling
from .scheduling.leveling_boundary import SchedulerLevelingInput
from .scheduling.schedule import ScheduleResult, schedule
from .scheduling.time_forward_pass import TimeScheduledActivity
from .scheduling.time_schedule import TimeScheduleOptions, TimeScheduleResult, time_schedule


class ScheduleEvaluationError(ValueError):
    """Raised when an immutable snapshot cannot be evaluated safely."""


@dataclass(frozen=True)
class ScheduleEvaluationResult:
    """Auditable result of one authoritative scheduling calculation."""

    snapshot_id: str
    snapshot_hash: str
    calculation_identity: str
    calculation_run_identity: str
    project_id: str
    project_revision: int
    mode: str
    date_result: ScheduleResult | None = None
    time_activities: Mapping[str, TimeScheduledActivity] | None = None
    time_result: TimeScheduleResult | None = None

    @property
    def project_finish(self) -> date | datetime:
        if self.date_result is not None:
            return self.date_result.project_finish
        if self.time_activities:
            return max(item.finish for item in self.time_activities.values())
        raise ScheduleEvaluationError("EVALUATION_HAS_NO_ACTIVITIES")


def evaluate_schedule_snapshot(
    snapshot: ScheduleInputSnapshot,
    calculation_context: CalculationContext,
    calendar_registry: CalendarResolverRegistry,
    *,
    leveling_input: SchedulerLevelingInput | None = None,
) -> ScheduleEvaluationResult:
    """Materialize and evaluate one immutable snapshot.

    The evaluator never reads mutable repositories during calculation. The
    snapshot and CalculationContext are the complete calculation inputs.

    Resource-leveling ScheduleOptions are routed explicitly through the
    authoritative leveling seam when the application supplies its already
    mapped SchedulerLevelingInput. Plain scheduling remains unchanged.
    """
    if calculation_context.input_snapshot_id != snapshot.snapshot_id:
        raise ScheduleEvaluationError("INPUT_SNAPSHOT_ID_MISMATCH")
    if calculation_context.project_id != snapshot.scope.project_id:
        raise ScheduleEvaluationError("PROJECT_ID_MISMATCH")
    if calculation_context.project_version != snapshot.scope.project_revision:
        raise ScheduleEvaluationError("PROJECT_REVISION_MISMATCH")
    if calculation_context.tenant_id is not None and calculation_context.tenant_id != snapshot.scope.tenant_id:
        raise ScheduleEvaluationError("TENANT_ID_MISMATCH")
    if calculation_context.calculation_identity != snapshot.calculation_identity:
        raise ScheduleEvaluationError("CALCULATION_IDENTITY_MISMATCH")

    materialized = materialize_schedule_snapshot(snapshot, calendar_registry)
    return _evaluate_materialized(
        materialized,
        snapshot,
        calculation_context,
        leveling_input=leveling_input,
    )


def _evaluate_materialized(
    materialized: MaterializedScheduleInput,
    snapshot: ScheduleInputSnapshot,
    calculation_context: CalculationContext,
    *,
    leveling_input: SchedulerLevelingInput | None = None,
) -> ScheduleEvaluationResult:
    source = materialized.schedule_input
    try:
        if source.mode.value == "DATE_BASED":
            resolver = materialized.calendar_registry.resolve(source.project_calendar)
            leveling_requested = _resource_leveling_requested(source.schedule_options)
            if leveling_requested:
                if leveling_input is None:
                    raise ScheduleEvaluationError("SCHEDULE_LEVELING_INPUT_REQUIRED")
                result, _, _ = schedule_with_resource_leveling(
                    activities=source.activities,
                    relationships=source.relationships,
                    project_start=source.project_start,
                    resolver=resolver,
                    leveling_input=leveling_input,
                    project_finish=source.project_finish,
                    constraints=source.constraints,
                    options=source.schedule_options,
                    calculation_context=calculation_context,
                )
            else:
                result = schedule(
                    activities=source.activities,
                    relationships=source.relationships,
                    project_start=source.project_start,
                    resolver=resolver,
                    project_finish=source.project_finish,
                    constraints=source.constraints,
                    options=source.schedule_options,
                    calculation_context=calculation_context,
                )
            run_identity = _run_identity(
                snapshot.snapshot_hash,
                calculation_context.calculation_identity,
                _canonical_result(result),
            )
            return ScheduleEvaluationResult(
                snapshot_id=snapshot.snapshot_id,
                snapshot_hash=snapshot.snapshot_hash,
                calculation_identity=calculation_context.calculation_identity,
                calculation_run_identity=run_identity,
                project_id=source.project_id,
                project_revision=source.project_revision,
                mode=source.mode.value,
                date_result=result,
            )

        activities = source.activities
        relationships = source.relationships
        constraints = source.constraints
        timed_result = time_schedule(
            activities=activities,
            relationships=relationships,
            project_start=source.project_start,
            project_finish=source.project_finish,
            registry=materialized.calendar_registry,
            constraints=constraints,
            options=TimeScheduleOptions(
                relationship_lag_calendar=source.schedule_options.relationship_lag_calendar,
                start_to_start_lag_calculation_type=source.schedule_options.start_to_start_lag_calculation_type,
                data_date=(
                    datetime.combine(
                        source.schedule_options.data_date,
                        datetime.min.time(),
                        tzinfo=source.project_start.tzinfo,
                    )
                    if source.schedule_options.data_date is not None
                    else None
                ),
            ),
        )
        run_identity = _run_identity(
            snapshot.snapshot_hash,
            calculation_context.calculation_identity,
            _canonical_result(timed_result),
        )
        return ScheduleEvaluationResult(
            snapshot_id=snapshot.snapshot_id,
            snapshot_hash=snapshot.snapshot_hash,
            calculation_identity=calculation_context.calculation_identity,
            calculation_run_identity=run_identity,
            project_id=source.project_id,
            project_revision=source.project_revision,
            mode=source.mode.value,
            time_activities=timed_result.early_activities,
            time_result=timed_result,
        )
    except ScheduleEvaluationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ScheduleEvaluationError("SCHEDULE_EVALUATION_FAILED") from exc


def _resource_leveling_requested(options: object) -> bool:
    return any(
        getattr(options, name)
        for name in (
            "level_all_resources",
            "level_within_float",
            "min_float_to_preserve",
            "over_allocation_percentage",
            "resource_list",
            "priority_list",
            "preserve_scheduled_early_and_late_dates",
        )
    )


def _canonical_result(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_result(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical_result(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _canonical_result(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        raw = getattr(value, "value")
        if isinstance(raw, (str, int, float, bool)):
            return raw
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _run_identity(snapshot_hash: str, calculation_identity: str, result: object) -> str:
    payload = json.dumps(
        {
            "snapshot_hash": snapshot_hash,
            "calculation_identity": calculation_identity,
            "result": _canonical_result(result),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
