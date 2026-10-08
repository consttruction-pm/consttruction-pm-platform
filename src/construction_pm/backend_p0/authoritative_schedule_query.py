from __future__ import annotations

"""Schedule Query -> authoritative scheduling application adapter."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Mapping

from construction_pm.backend_p0.schedule_query import ScheduleQueryApplicationService
from construction_pm.backend_p0.models import BackendScope
from construction_pm.application.authorization import AuthorizationContext, AuthorizationPolicy

from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.control_intelligence.graph import ControlDomain
from construction_pm.control_intelligence.scenario import ScenarioChange
from construction_pm.control_intelligence.query import ScheduleQueryAnswer, ScheduleQueryKind, ScheduleQueryRequest
from construction_pm.schedule_evaluator import ScheduleEvaluationResult, evaluate_schedule_snapshot
from construction_pm.schedule_input_snapshot_repository import ScheduleInputSnapshot, ScheduleInputSnapshotRepository
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

        if request.kind is ScheduleQueryKind.SCENARIO:
            _validate_snapshot_context(snapshot, calculation_context)
            source = SourceReference(
                source_id=snapshot.snapshot_id,
                source_type="schedule-input-snapshot",
                locator=f"/schedule/input-snapshots/{snapshot.snapshot_id}",
                revision=request.scope.project_revision,
                content_hash=snapshot.snapshot_hash,
            )
            data = _project_result(request, None, source)
            return ScheduleQueryAnswer(
                query_id=request.query_id,
                scope=request.scope,
                answer_key="schedule.query.result",
                data=data,
                source_refs=(source,),
            )

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

        data = _project_result(request, result, source)
        return ScheduleQueryAnswer(
            query_id=request.query_id,
            scope=request.scope,
            answer_key="schedule.query.result",
            data=data,
            source_refs=(source,),
        )


def _project_result(
    request: ScheduleQueryRequest,
    result: ScheduleEvaluationResult | None,
    source: SourceReference,
) -> Mapping[str, object]:
    if request.kind is ScheduleQueryKind.SCENARIO:
        return _project_scenario_proposal(request, source)
    if result is None:
        raise ValueError("SCHEDULE_EVALUATION_RESULT_REQUIRED")
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
            requested_ids = request.constraints.get("activity_ids")
            if requested_ids is None:
                selected_ids = set(activities)
            elif isinstance(requested_ids, (list, tuple, set, frozenset)):
                selected_ids = {str(item) for item in requested_ids}
            else:
                raise ValueError("INVALID_SCHEDULE_QUERY_FILTER")
            selected = {
                key: {
                    "start": value.start.isoformat(),
                    "finish": value.finish.isoformat(),
                    "duration": value.duration,
                }
                for key, value in sorted(activities.items())
                if key in selected_ids
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


def _validate_snapshot_context(
    snapshot: ScheduleInputSnapshot,
    calculation_context: CalculationContext,
) -> None:
    if calculation_context.input_snapshot_id != snapshot.snapshot_id:
        raise ValueError("INPUT_SNAPSHOT_ID_MISMATCH")
    if calculation_context.project_id != snapshot.scope.project_id:
        raise ValueError("PROJECT_ID_MISMATCH")
    if calculation_context.project_version != snapshot.scope.project_revision:
        raise ValueError("PROJECT_REVISION_MISMATCH")
    if calculation_context.tenant_id is not None and calculation_context.tenant_id != snapshot.scope.tenant_id:
        raise ValueError("TENANT_ID_MISMATCH")
    if calculation_context.calculation_identity != snapshot.calculation_identity:
        raise ValueError("CALCULATION_IDENTITY_MISMATCH")


def _project_scenario_proposal(request: ScheduleQueryRequest, source: SourceReference) -> Mapping[str, object]:
    raw_changes = request.constraints.get("changes")
    if not isinstance(raw_changes, (list, tuple)) or not raw_changes:
        raise ValueError("SCENARIO_CHANGES_REQUIRED")
    changes: list[ScenarioChange] = []
    for raw in raw_changes:
        if not isinstance(raw, Mapping):
            raise ValueError("INVALID_SCENARIO_CHANGE")
        try:
            change = ScenarioChange(
                change_id=str(raw["change_id"]),
                domain=ControlDomain(str(raw["domain"])),
                entity_type=str(raw["entity_type"]),
                entity_id=str(raw["entity_id"]),
                operation=str(raw["operation"]),
                proposed_value=dict(raw.get("proposed_value", {})),
                source_refs=(source,),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("INVALID_SCENARIO_CHANGE") from exc
        changes.append(change)
    return {
        "scenario_id": request.query_id,
        "purpose_key": request.query_text,
        "authoritative_mutation_allowed": False,
        "proposed_changes": [
            {"change_id": c.change_id, "domain": c.domain.value, "entity_type": c.entity_type,
             "entity_id": c.entity_id, "operation": c.operation, "proposed_value": dict(c.proposed_value)}
            for c in changes
        ],
        "source_ids": [source.source_id],
        "status": "proposal_only",
    }


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
