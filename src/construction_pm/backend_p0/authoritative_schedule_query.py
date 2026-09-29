from __future__ import annotations

"""Schedule Query -> authoritative scheduling application adapter."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Mapping

from construction_pm.backend_p0.schedule_query import ScheduleQueryApplicationService
from construction_pm.backend_p0.models import BackendScope
from construction_pm.application.authorization import AuthorizationContext, AuthorizationPolicy

from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.control_intelligence.query import ScheduleQueryAnswer, ScheduleQueryKind, ScheduleQueryRequest
from construction_pm.schedule_evaluator import ScheduleEvaluationResult, evaluate_schedule_snapshot
from construction_pm.schedule_input_snapshot_repository import ScheduleInputSnapshotRepository
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext


@dataclass(frozen=True)
class AuthoritativeScheduleQueryProvider:
    """Executes a query against one immutable schedule snapshot.

    Natural-language interpretation is intentionally outside this adapter.
    The query kind and constraints select deterministic projections of the
    already-calculated schedule result.
    """

    snapshot_repository: ScheduleInputSnapshotRepository
    calendar_registry_factory: Callable[[], CalendarResolverRegistry]

    def execute(
        self,
        request: ScheduleQueryRequest,
        *,
        calculation_context: CalculationContext,
    ) -> ScheduleQueryAnswer:
        snapshot = self.snapshot_repository.get(
            BackendScope(
                request.scope.tenant_id,
                request.scope.project_id,
                request.scope.project_revision,
            ),
            calculation_context.input_snapshot_id,
        )
        if snapshot is None:
            raise ValueError("SCHEDULE_INPUT_SNAPSHOT_NOT_FOUND")

        result = evaluate_schedule_snapshot(
            snapshot,
            calculation_context,
            self.calendar_registry_factory(),
        )
        source = SourceReference(
            source_id=snapshot.snapshot_id,
            source_type="schedule-calculation",
            locator=f"/schedule/evaluations/{result.calculation_run_identity}",
            revision=request.scope.project_revision,
            content_hash=result.calculation_run_identity,
        )

        data = _project_result(request, result)
        return ScheduleQueryAnswer(
            query_id=request.query_id,
            scope=request.scope,
            answer_key="schedule.query.result",
            data=data,
            source_refs=(source,),
        )


def _project_result(
    request: ScheduleQueryRequest,
    result: ScheduleEvaluationResult,
) -> Mapping[str, object]:
    if result.date_result is not None:
        activities = result.date_result.activities
        if request.kind is ScheduleQueryKind.FACT:
            return {
                "calculation_run_identity": result.calculation_run_identity,
                "project_finish": result.project_finish.isoformat(),
                "activity_count": len(activities),
                "activities": {
                    key: {
                        "start": value.start.isoformat(),
                        "finish": value.finish.isoformat(),
                        "duration": value.duration,
                    }
                    for key, value in sorted(activities.items())
                },
            }

        if request.kind is ScheduleQueryKind.FILTER:
            status = str(request.constraints.get("status", "")).lower()
            selected = {
                key: {
                    "start": value.start.isoformat(),
                    "finish": value.finish.isoformat(),
                    "duration": value.duration,
                }
                for key, value in sorted(activities.items())
                if not status or str(getattr(value, "status", "")).lower() == status
            }
            return {
                "calculation_run_identity": result.calculation_run_identity,
                "activities": selected,
                "count": len(selected),
            }

        if request.kind is ScheduleQueryKind.EXPLANATION:
            return {
                "calculation_run_identity": result.calculation_run_identity,
                "project_finish": result.project_finish.isoformat(),
                "activity_count": len(activities),
                "explanation_key": "schedule.query.explanation.calculated_from_snapshot",
            }

    if result.time_activities is not None:
        if request.kind is ScheduleQueryKind.FACT:
            return {
                "calculation_run_identity": result.calculation_run_identity,
                "activity_count": len(result.time_activities),
                "project_finish": result.project_finish.isoformat(),
                "activities": {
                    key: {
                        "start": value.start.isoformat(),
                        "finish": value.finish.isoformat(),
                    }
                    for key, value in sorted(result.time_activities.items())
                },
            }

        if request.kind is ScheduleQueryKind.EXPLANATION:
            return {
                "calculation_run_identity": result.calculation_run_identity,
                "project_finish": result.project_finish.isoformat(),
                "activity_count": len(result.time_activities),
                "explanation_key": "schedule.query.explanation.calculated_from_snapshot",
            }

    raise ValueError("UNSUPPORTED_SCHEDULE_QUERY_PROJECTION")


@dataclass(frozen=True)
class AuthoritativeScheduleQueryApplicationService:
    provider: AuthoritativeScheduleQueryProvider
    authorization_policy: AuthorizationPolicy

    def execute(
        self,
        request: ScheduleQueryRequest,
        *,
        auth_context: AuthorizationContext,
        calculation_context: CalculationContext,
    ) -> ScheduleQueryAnswer:
        return ScheduleQueryApplicationService(
            _ContextBoundProvider(self.provider, calculation_context),
            self.authorization_policy,
        ).execute(request, auth_context=auth_context)


@dataclass(frozen=True)
class _ContextBoundProvider:
    provider: AuthoritativeScheduleQueryProvider
    calculation_context: CalculationContext

    def execute(self, request: ScheduleQueryRequest) -> ScheduleQueryAnswer:
        return self.provider.execute(
            request,
            calculation_context=self.calculation_context,
        )
