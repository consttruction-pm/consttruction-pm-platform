from __future__ import annotations

"""Transport-independent runtime entry point for the canonical Python Shared Core.

The runtime is intentionally independent of WSGI, HTTP, browser state and client UI.
A trusted host supplies the authenticated AuthorizationContext and platform-specific
repositories. The JSON envelope is suitable for a native Windows/Flutter bridge.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
)
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.backend_p0.schedule_query import (
    SCHEDULE_QUERY_VERSION,
    ScheduleQueryAPI,
    ScheduleQueryApplicationService,
)
from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.query import (
    ScheduleQueryKind,
    ScheduleQueryRequest,
)
from construction_pm.schedule_calculation_context_repository import (
    CalculationContextRepository,
)
from construction_pm.schedule_input_snapshot_repository import (
    ScheduleInputSnapshot,
    ScheduleInputSnapshotRepository,
)
from construction_pm.scheduling.calendar_context import CalendarResolverRegistry
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput


CORE_RUNTIME_CONTRACT_VERSION = "cubi.shared-core-runtime.v1"
SCHEDULE_QUERY_OPERATION = "schedule.query"


def _error(category: str, code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "category": category,
            "code": code,
            "message": message,
            "retryable": False,
        }
    }


def _response(operation: str, result: Mapping[str, object]) -> str:
    return json.dumps(
        {
            "contract_version": CORE_RUNTIME_CONTRACT_VERSION,
            "operation": operation,
            "result": dict(result),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _schedule_request(payload: object) -> ScheduleQueryRequest:
    if not isinstance(payload, Mapping):
        raise ValueError("CORE_RUNTIME_PAYLOAD_INVALID")
    if payload.get("contract_version") != SCHEDULE_QUERY_VERSION:
        raise ValueError("UNSUPPORTED_SCHEDULE_QUERY_CONTRACT")

    required = ("query_id", "scope", "requested_by", "query_text", "kind", "language")
    if any(name not in payload for name in required):
        raise ValueError("CORE_RUNTIME_PAYLOAD_INVALID")

    raw_scope = payload.get("scope")
    if not isinstance(raw_scope, Mapping):
        raise ValueError("CORE_RUNTIME_SCOPE_INVALID")
    constraints = payload.get("constraints", {})
    if not isinstance(constraints, Mapping):
        raise ValueError("CORE_RUNTIME_CONSTRAINTS_INVALID")

    return ScheduleQueryRequest(
        query_id=payload["query_id"],
        scope=ControlScope(
            tenant_id=raw_scope.get("tenant_id"),
            project_id=raw_scope.get("project_id"),
            project_revision=raw_scope.get("project_revision"),
        ),
        requested_by=payload["requested_by"],
        query_text=payload["query_text"],
        kind=ScheduleQueryKind(payload["kind"]),
        language=payload["language"],
        constraints=dict(constraints),
    )


@dataclass(frozen=True)
class SharedCoreRuntime:
    """Reusable Python runtime over the existing authoritative application API."""

    schedule_query_api: ScheduleQueryAPI

    def execute_schedule_query(
        self,
        request: ScheduleQueryRequest,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object]:
        """Execute one query using host-authenticated identity and shared policy."""
        try:
            auth_context.validate()
        except AuthorizationError:
            return _error(
                "authorization",
                "INVALID_AUTHORIZATION_CONTEXT",
                "The host supplied an invalid authorization context.",
            )
        if request.requested_by != auth_context.user_id:
            return _error(
                "authorization",
                "REQUESTED_BY_MISMATCH",
                "The request actor does not match the authenticated host identity.",
            )
        return self.schedule_query_api.execute(request, auth_context=auth_context)

    def dispatch_json(
        self,
        request_json: str,
        *,
        auth_context: AuthorizationContext,
    ) -> str:
        """Dispatch the versioned JSON ABI; identity/roles are supplied out-of-band."""
        if not isinstance(request_json, str):
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The runtime request must be JSON text."),
            )
        try:
            envelope = json.loads(request_json)
        except (json.JSONDecodeError, TypeError):
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The runtime request is not valid JSON."),
            )
        if not isinstance(envelope, Mapping):
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The runtime request must be a JSON object."),
            )
        if envelope.get("contract_version") != CORE_RUNTIME_CONTRACT_VERSION:
            return _response(
                "runtime.error",
                _error("validation", "UNSUPPORTED_CORE_RUNTIME_CONTRACT", "The runtime contract version is not supported."),
            )

        operation = envelope.get("operation")
        if operation != SCHEDULE_QUERY_OPERATION:
            return _response(
                "runtime.error",
                _error("validation", "UNSUPPORTED_CORE_RUNTIME_OPERATION", "The requested runtime operation is not supported."),
            )
        try:
            request = _schedule_request(envelope.get("payload"))
        except (KeyError, TypeError, ValueError):
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The schedule query payload is invalid."),
            )

        result = self.execute_schedule_query(request, auth_context=auth_context)
        return _response(SCHEDULE_QUERY_OPERATION, result)


def build_shared_core_runtime(
    *,
    snapshot_repository: ScheduleInputSnapshotRepository,
    calendar_registry_factory: Callable[[], CalendarResolverRegistry],
    calculation_context_repository: CalculationContextRepository,
    authorization_policy: AuthorizationPolicy,
    leveling_input_resolver: Callable[
        [ScheduleInputSnapshot, CalculationContext, CalendarResolverRegistry, AuthorizationContext],
        SchedulerLevelingInput | None,
    ] | None = None,
) -> SharedCoreRuntime:
    """Compose the same Shared Core Schedule Query runtime for server or local hosts.

    The caller owns identity, repositories, calendar registry and any persisted
    resource-leveling resolver. This function owns no database, network or UI.
    """
    provider = AuthoritativeScheduleQueryProvider(
        snapshot_repository=snapshot_repository,
        calendar_registry_factory=calendar_registry_factory,
        calculation_context_repository=calculation_context_repository,
        leveling_input_resolver=leveling_input_resolver,
    )
    schedule_query_api = ScheduleQueryAPI(
        ScheduleQueryApplicationService(
            provider=provider,
            authorization_policy=authorization_policy,
        )
    )
    return SharedCoreRuntime(schedule_query_api=schedule_query_api)


__all__ = [
    "CORE_RUNTIME_CONTRACT_VERSION",
    "SCHEDULE_QUERY_OPERATION",
    "SharedCoreRuntime",
    "build_shared_core_runtime",
]
