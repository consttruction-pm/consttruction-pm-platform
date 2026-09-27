from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from construction_pm.control_intelligence.contracts import ControlScope

from .errors import BackendApplicationError, ErrorCategory
from construction_pm.control_intelligence.query import (
    ScheduleQueryAnswer,
    ScheduleQueryRequest,
)


SCHEDULE_QUERY_VERSION = "schedule-query.v1"
SCHEDULE_QUERY_RESULT_VERSION = "schedule-query-result.v1"


class ScheduleQueryProvider(Protocol):
    """Adapter to the authoritative query evaluator.

    This boundary deliberately does not implement scheduling or financial
    calculations. The provider owns the existing Core semantics.
    """

    def execute(self, request: ScheduleQueryRequest) -> ScheduleQueryAnswer: ...


@dataclass(frozen=True)
class ScheduleQueryApplicationService:
    provider: ScheduleQueryProvider
    authorization_policy: AuthorizationPolicy

    def execute(
        self,
        request: ScheduleQueryRequest,
        *,
        auth_context: AuthorizationContext,
    ) -> ScheduleQueryAnswer:
        self._authorize(request.scope, auth_context)
        answer = self.provider.execute(request)
        if not isinstance(answer, ScheduleQueryAnswer):
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "INVALID_SCHEDULE_QUERY_RESULT",
                "Schedule query provider returned an invalid result",
            )
        if answer.query_id != request.query_id:
            raise BackendApplicationError(
                ErrorCategory.CONFLICT,
                "SCHEDULE_QUERY_RESULT_ID_MISMATCH",
                "Schedule query result id does not match the request",
            )
        if answer.scope != request.scope:
            raise BackendApplicationError(
                ErrorCategory.CONFLICT,
                "SCHEDULE_QUERY_RESULT_SCOPE_MISMATCH",
                "Schedule query result scope does not match the request",
            )
        return answer

    def _authorize(
        self,
        scope: ControlScope,
        auth_context: AuthorizationContext,
    ) -> None:
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
        ):
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "CROSS_SCOPE_ACCESS",
                "Authorization context does not match the query scope",
            )
        if not self.authorization_policy.is_allowed(
            auth_context, Permission.PROJECT_READ
        ):
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "FORBIDDEN",
                "Operation is not authorized",
            )


@dataclass(frozen=True)
class ScheduleQueryAPI:
    service: ScheduleQueryApplicationService

    def execute(
        self,
        request: ScheduleQueryRequest,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object]:
        try:
            answer = self.service.execute(request, auth_context=auth_context)
        except BackendApplicationError as exc:
            return exc.to_dto()

        return {
            "contract_version": SCHEDULE_QUERY_RESULT_VERSION,
            "query_id": answer.query_id,
            "scope": {
                "tenant_id": answer.scope.tenant_id,
                "project_id": answer.scope.project_id,
                "project_revision": answer.scope.project_revision,
            },
            "answer_key": answer.answer_key,
            "data": dict(answer.data),
            "source_refs": [
                {
                    "source_id": source.source_id,
                    "source_type": source.source_type,
                    "locator": source.locator,
                    "revision": source.revision,
                    **(
                        {"excerpt_key": source.excerpt_key}
                        if source.excerpt_key is not None
                        else {}
                    ),
                    **(
                        {"content_hash": source.content_hash}
                        if source.content_hash is not None
                        else {}
                    ),
                }
                for source in answer.source_refs
            ],
            "proposed_actions": [
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type,
                    "title_key": action.title_key,
                    "requires_approval": action.requires_approval,
                    "source_refs": [
                        {
                            "source_id": source.source_id,
                            "source_type": source.source_type,
                            "locator": source.locator,
                            "revision": source.revision,
                        }
                        for source in action.source_refs
                    ],
                }
                for action in answer.proposed_actions
            ],
        }


__all__ = [
    "SCHEDULE_QUERY_RESULT_VERSION",
    "SCHEDULE_QUERY_VERSION",
    "ScheduleQueryAPI",
    "ScheduleQueryApplicationService",
    "ScheduleQueryProvider",
]
