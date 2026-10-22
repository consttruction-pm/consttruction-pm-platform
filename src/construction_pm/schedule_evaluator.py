from __future__ import annotations

"""Authoritative snapshot -> Shared Scheduling Core evaluation boundary."""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime
from typing import Mapping

from .schedule_input_snapshot_repository import ScheduleInputSnapshot
from .schedule_snapshot_materializer import MaterializedScheduleInput, materialize_schedule_snapshot
from .scheduling.calendar_context import CalendarResolverRegistry
from .scheduling.calculation_context import CalculationContext
from .scheduling.forward_pass import ScheduledActivity
from .scheduling.activity import ActivityType
from .scheduling.leveling_scheduler import (
    _schedule_options_without_leveling,
    schedule_with_resource_leveling,
)
from .scheduling.leveling_boundary import (
    SchedulerLevelingInput,
    scheduler_leveling_input_from_options,
)
from .scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceDemand,
)
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

    Identity compatibility:
    - New snapshots bind to deterministic v2 semantic identity.
    - Pre-v2 snapshots remain explicitly supported until migrated.

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
    if snapshot.calculation_identity_version == 2:
        identity_matches = (
            calculation_context.calculation_identity == snapshot.calculation_identity
        )
    elif snapshot.calculation_identity_version == 1:
        identity_matches = (
            calculation_context.legacy_calculation_identity == snapshot.calculation_identity
        )
    else:
        raise ScheduleEvaluationError("INVALID_CALCULATION_IDENTITY_VERSION")
    if not identity_matches:
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
                if source.resource_leveling_inputs is not None:
                    if leveling_input is not None:
                        raise ScheduleEvaluationError(
                            "EXTERNAL_LEVELING_INPUT_CANNOT_OVERRIDE_SNAPSHOT_INPUT"
                        )
                    leveling_input = _leveling_input_from_snapshot_facts(
                        source,
                        resolver=resolver,
                        calculation_context=calculation_context,
                    )
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


def _leveling_input_from_snapshot_facts(
    source: object,
    *,
    resolver: object,
    calculation_context: CalculationContext,
) -> SchedulerLevelingInput:
    """Build typed leveling rows only from the same immutable schedule snapshot."""
    facts = getattr(source, "resource_leveling_inputs", None)
    if facts is None:
        raise ScheduleEvaluationError("SCHEDULE_LEVELING_INPUT_REQUIRED")
    activities = tuple(getattr(source, "activities", ()))
    relationships = tuple(getattr(source, "relationships", ()))
    project_start = getattr(source, "project_start", None)
    project_finish = getattr(source, "project_finish", None)
    constraints = tuple(getattr(source, "constraints", ()))
    schedule_options = getattr(source, "schedule_options", None)
    if not activities or not isinstance(project_start, date) or isinstance(project_start, datetime):
        raise ScheduleEvaluationError("INVALID_RESOURCE_LEVELING_SCHEDULE_SOURCE")

    # The existing Shared Scheduling Core calculates the authoritative early,
    # late and float values first. The leveling rows are only a transport slice;
    # they do not derive or approximate CPM dates/floats.
    initial = schedule(
        activities=activities,
        relationships=relationships,
        project_start=project_start,
        resolver=resolver,
        project_finish=project_finish,
        constraints=constraints,
        options=_schedule_options_without_leveling(schedule_options),
        calculation_context=calculation_context,
    )
    early_schedule = initial.early_activities or initial.activities
    late_schedule = initial.late_activities or initial.activities
    demand_by_activity: dict[str, list[ResourceDemand]] = {
        activity.id: [] for activity in activities
    }
    # P6 v26 explicitly ignores WBS Summary activities during resource
    # leveling. Keep their raw assignments in the immutable snapshot for audit,
    # but do not turn those summary rollups into capacity-consuming demands.
    wbs_summary_ids = {
        activity.id
        for activity in activities
        if getattr(activity, "activity_type", None) is ActivityType.WBS_SUMMARY
    }
    for demand in facts.demands:
        if demand.activity_id in wbs_summary_ids:
            continue
        demand_by_activity[demand.activity_id].append(
            ResourceDemand(
                resource_id=demand.resource_id,
                period=demand.period,
                units=demand.units,
                activity_id=demand.activity_id,
            )
        )

    forward_rows: list[LevelingActivity] = []
    backward_rows: list[BackwardLevelingActivity] = []
    for activity in sorted(activities, key=lambda item: item.id):
        early = early_schedule.get(activity.id)
        late = late_schedule.get(activity.id)
        float_values = initial.floats.get(activity.id)
        if early is None or late is None or float_values is None:
            raise ScheduleEvaluationError(
                f"SCHEDULE_MISSING_LEVELING_ACTIVITY:{activity.id}"
            )
        demands = tuple(sorted(
            demand_by_activity.get(activity.id, ()),
            key=lambda item: (item.period, item.resource_id, item.activity_id or ""),
        ))
        original_duration = Decimal(
            activity.original_duration
            if activity.original_duration is not None
            else activity.duration
        )
        remaining_duration = Decimal(
            activity.remaining_duration
            if activity.remaining_duration is not None
            else activity.duration
        )
        metadata = {
            "activity_priority": None,
            "total_float": float_values.total_float,
            "free_float": float_values.free_float,
            "original_planned_duration": original_duration,
            "planned_finish": activity.planned_finish,
            "project_planned_start": project_start,
            "project_priority": source.project_leveling_priority,
            "remaining_duration": remaining_duration,
            "leveling_priority": activity.leveling_priority,
        }
        forward_rows.append(LevelingActivity(
            activity_id=activity.id,
            start=early.start,
            finish=early.finish,
            resource_demands=demands,
            **metadata,
        ))
        # A finish constraint can legitimately create negative float, with
        # late dates preceding early dates. Keep the authoritative negative
        # float, but bound the backward leveling proposal window to CPM early
        # dates, matching the Shared Core's existing intermediate-pass builder.
        candidate_late_start = max(late.start, early.start)
        candidate_late_finish = max(late.finish, early.finish)
        backward_rows.append(BackwardLevelingActivity(
            activity_id=activity.id,
            early_start=early.start,
            early_finish=early.finish,
            late_start=candidate_late_start,
            late_finish=candidate_late_finish,
            resource_demands=demands,
            activity_priority=None,
            total_float=float_values.total_float,
            free_float=float_values.free_float,
            original_planned_duration=original_duration,
            planned_finish=activity.planned_finish,
            project_planned_start=project_start,
            project_priority=source.project_leveling_priority,
            remaining_duration=remaining_duration,
            leveling_priority=activity.leveling_priority,
        ))

    return scheduler_leveling_input_from_options(
        forward_activities=tuple(forward_rows),
        backward_activities=tuple(backward_rows),
        capacities=facts.capacities,
        options=schedule_options,
    )


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
