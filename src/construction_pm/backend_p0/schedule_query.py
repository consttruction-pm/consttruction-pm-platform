from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from construction_pm.control_intelligence.contracts import ControlScope
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
            raise ValueError("INVALID_SCHEDULE_QUERY_RESULT")
        if answer.query_id != request.query_id:
            raise ValueError("SCHEDULE_QUERY_RESULT_ID_MISMATCH")
        if answer.scope != request.scope:
            raise ValueError("SCHEDULE_QUERY_RESULT_SCOPE_MISMATCH")
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
            raise PermissionError("CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(
            auth_context, Permission.PROJECT_READ
        ):
            raise PermissionError("FORBIDDEN")


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
        except PermissionError as exc:
            return {
                "error": {
                    "category": "authorization",
                    "code": str(exc),
                    "message": str(exc),
                }
            }
        except ValueError as exc:
            return {
                "error": {
                    "category": "validation",
                    "code": str(exc),
                    "message": str(exc),
                }
            }

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
