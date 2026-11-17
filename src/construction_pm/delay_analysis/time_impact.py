from __future__ import annotations

"""Fragnet insertion and authoritative Shared Core time-impact execution.

This is a schedule what-if execution boundary, not a parallel CPM engine.
Both schedules are evaluated by the canonical evaluate_schedule_snapshot.
"""

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Callable
from uuid import uuid4

from ..schedule_evaluator import evaluate_schedule_snapshot
from ..schedule_input_snapshot_repository import ScheduleInputSnapshotRepository, build_snapshot
from ..schedule_run_capture import ScheduleRunCapture, ScheduleRunCaptureRepository, build_schedule_run_capture
from ..schedule_snapshot_materializer import materialize_schedule_snapshot
from ..scheduling.activity import Activity
from ..scheduling.authoritative_schedule import ActivityCalendarAssignment, AuthoritativeScheduleMode
from ..scheduling.calculation_context import CalculationContext
from ..scheduling.calendar_context import CalendarResolverRegistry
from ..scheduling.relationships import Relationship
from .fragnet import DelayEventFragnet, FragnetValidationError


class TimeImpactExecutionError(ValueError):
    """Raised when an inserted-fragnet scenario cannot be executed safely."""


@dataclass(frozen=True)
class TimeImpactAssessment:
    event_id: str
    source_snapshot_id: str
    source_snapshot_hash: str
    impacted_snapshot_id: str
    impacted_snapshot_hash: str
    baseline_run: ScheduleRunCapture
    impacted_run: ScheduleRunCapture
    unimpacted_project_finish: str
    impacted_project_finish: str
    project_finish_delta_calendar_days: int
    added_activity_ids: tuple[str, ...]
    analysis_hash: str
    method: str = "P6_EPPM_STYLE_INSERTED_FRAGNET_WHAT_IF"
    limitations: tuple[str, ...] = (
        "This is a deterministic schedule impact scenario, not a finding of causation or contractual entitlement.",
        "The source snapshot must represent the contemporaneous statused schedule appropriate to the selected analysis date.",
        "The result is only as complete as the source snapshot, calendars, constraints, resource facts and Shared Core capabilities.",
        "No concurrency, responsibility, extension-of-time, damages, or cost conclusion is made.",
        "The captured Schedule Project Log envelope remains partial where Shared Core does not expose native P6 log sections.",
    )


def _analysis_hash(event_id, source_hash, impacted_hash, baseline_run, impacted_run, delta):
    payload = json.dumps(
        {
            "method": "P6_EPPM_STYLE_INSERTED_FRAGNET_WHAT_IF",
            "event_id": event_id,
            "source_snapshot_hash": source_hash,
            "impacted_snapshot_hash": impacted_hash,
            "baseline_run_id": baseline_run.run_id,
            "impacted_run_id": impacted_run.run_id,
            "unimpacted_finish": baseline_run.project_finish,
            "impacted_finish": impacted_run.project_finish,
            "project_finish_delta_calendar_days": delta,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TimeImpactAnalysisExecutor:
    """Insert a validated event fragnet and rerun the authoritative scheduler.

    The caller supplies server-trusted immutable records through an authorized
    application boundary. No HTTP route or client-asserted tenant identity is
    introduced by this domain service.
    """

    def __init__(
        self,
        *,
        snapshot_repository: ScheduleInputSnapshotRepository,
        run_repository: ScheduleRunCaptureRepository,
        snapshot_id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.snapshot_repository = snapshot_repository
        self.run_repository = run_repository
        self.snapshot_id_factory = snapshot_id_factory or (lambda: str(uuid4()))
        self.clock = clock or (lambda: datetime.now().astimezone())

    def execute(
        self,
        source_snapshot,
        source_context: CalculationContext,
        calendar_registry: CalendarResolverRegistry,
        fragnet: DelayEventFragnet,
        *,
        leveling_input=None,
        cost_inputs=None,
        float_execution=None,
    ) -> TimeImpactAssessment:
        source_snapshot.validate()
        if source_context.input_snapshot_id != source_snapshot.snapshot_id:
            raise TimeImpactExecutionError("SOURCE_CONTEXT_SNAPSHOT_MISMATCH")
        if source_context.calculation_identity != source_snapshot.calculation_identity:
            raise TimeImpactExecutionError("SOURCE_CONTEXT_CALCULATION_IDENTITY_MISMATCH")
        if (
            source_context.project_id != source_snapshot.scope.project_id
            or source_context.project_version != source_snapshot.scope.project_revision
            or source_context.tenant_id not in (None, source_snapshot.scope.tenant_id)
        ):
            raise TimeImpactExecutionError("SOURCE_CONTEXT_SCOPE_MISMATCH")

        try:
            materialized = materialize_schedule_snapshot(source_snapshot, calendar_registry)
            source = materialized.schedule_input
            if source.mode is not AuthoritativeScheduleMode.DATE_BASED:
                raise TimeImpactExecutionError("FRAGNET_TIME_AWARE_MODE_NOT_YET_SUPPORTED")
            existing_ids = {item.id for item in source.activities}
            existing_pairs = {(item.predecessor_id, item.successor_id) for item in source.relationships}
            fragnet.validate_against(existing_ids, existing_pairs)

            new_activities = tuple(
                Activity(
                    id=item.activity_id,
                    name=item.name,
                    duration=item.duration_working_days,
                    activity_type=item.activity_type,
                )
                for item in fragnet.activities
            )
            new_relationships = tuple(
                Relationship(
                    predecessor_id=item.predecessor_id,
                    successor_id=item.successor_id,
                    type=item.relationship_type,
                    lag=item.lag_working_days,
                )
                for item in fragnet.relationships
            )
            new_calendar_assignments = tuple(
                ActivityCalendarAssignment(item.activity_id, item.calendar)
                for item in fragnet.activities if item.calendar is not None
            )
            impacted_id = self.snapshot_id_factory()
            if not isinstance(impacted_id, str) or not impacted_id.strip() or impacted_id == source_snapshot.snapshot_id:
                raise TimeImpactExecutionError("INVALID_IMPACTED_SNAPSHOT_ID")
            impacted_input = replace(
                source,
                snapshot_id=impacted_id,
                activities=source.activities + new_activities,
                relationships=source.relationships + new_relationships,
                constraints=source.constraints + fragnet.constraints,
                activity_calendar_assignments=source.activity_calendar_assignments + new_calendar_assignments,
            )
            now = self.clock()
            if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                raise TimeImpactExecutionError("TIME_IMPACT_CLOCK_MUST_BE_TIMEZONE_AWARE")
            impacted_context = CalculationContext(
                project_id=source_context.project_id,
                project_version=source_context.project_version,
                calendar_id=source_context.calendar_id,
                calendar_version=source_context.calendar_version,
                rules_version=source_context.rules_version,
                engine_version=source_context.engine_version,
                timezone=source_context.timezone,
                calculation_timestamp=now.isoformat(),
                input_snapshot_id=impacted_id,
                tenant_id=source_context.tenant_id,
                actor_id=source_context.actor_id,
                request_id=source_context.request_id,
                idempotency_key=f"{source_context.idempotency_key or 'tia'}:{fragnet.event_id}:{impacted_id}",
            )
            impacted_snapshot = build_snapshot(impacted_input, impacted_context, now)

            # Re-run the exact same authoritative evaluator for both snapshots.
            unimpacted_evaluation = evaluate_schedule_snapshot(
                source_snapshot, source_context, calendar_registry,
                leveling_input=leveling_input, cost_inputs=cost_inputs,
                float_execution=float_execution,
            )
            impacted_evaluation = evaluate_schedule_snapshot(
                impacted_snapshot, impacted_context, calendar_registry,
                leveling_input=leveling_input, cost_inputs=cost_inputs,
                float_execution=float_execution,
            )
            baseline_capture = build_schedule_run_capture(
                source_snapshot, source_context, unimpacted_evaluation, captured_at=now,
            )
            impacted_capture = build_schedule_run_capture(
                impacted_snapshot, impacted_context, impacted_evaluation, captured_at=now,
            )
            before_finish = unimpacted_evaluation.project_finish
            after_finish = impacted_evaluation.project_finish
            if type(before_finish) is not type(after_finish):
                raise TimeImpactExecutionError("SCHEDULE_FINISH_TYPE_MISMATCH")
            delta = (after_finish - before_finish).days

            # Persist only after both calculations and provenance records validate.
            self.snapshot_repository.save(impacted_snapshot)
            self.run_repository.save(baseline_capture)
            self.run_repository.save(impacted_capture)
            digest = _analysis_hash(
                fragnet.event_id, source_snapshot.snapshot_hash,
                impacted_snapshot.snapshot_hash, baseline_capture,
                impacted_capture, delta,
            )
            return TimeImpactAssessment(
                event_id=fragnet.event_id,
                source_snapshot_id=source_snapshot.snapshot_id,
                source_snapshot_hash=source_snapshot.snapshot_hash,
                impacted_snapshot_id=impacted_snapshot.snapshot_id,
                impacted_snapshot_hash=impacted_snapshot.snapshot_hash,
                baseline_run=baseline_capture,
                impacted_run=impacted_capture,
                unimpacted_project_finish=before_finish.isoformat(),
                impacted_project_finish=after_finish.isoformat(),
                project_finish_delta_calendar_days=delta,
                added_activity_ids=tuple(sorted(item.activity_id for item in fragnet.activities)),
                analysis_hash=digest,
            )
        except (FragnetValidationError, TimeImpactExecutionError):
            raise
        except (TypeError, ValueError, KeyError, ArithmeticError) as exc:
            raise TimeImpactExecutionError(f"TIME_IMPACT_EXECUTION_FAILED:{exc}") from exc
