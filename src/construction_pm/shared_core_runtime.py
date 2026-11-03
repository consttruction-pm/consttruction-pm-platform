from __future__ import annotations

"""Transport-independent runtime entry point for the canonical Python Shared Core.

The runtime is intentionally independent of WSGI, HTTP, browser state and client UI.
A trusted host supplies the authenticated AuthorizationContext, current project
revision and platform-specific repositories. JSON never supplies trusted identity,
permissions or revision authority.
"""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.backend_p0.schedule_query import (
    SCHEDULE_QUERY_VERSION,
    ScheduleQueryAPI,
    ScheduleQueryApplicationService,
)
from construction_pm.control_intelligence.contracts import ControlScope, MAX_SAFE_REVISION
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
MAX_RUNTIME_REQUEST_BYTES = 1_048_576
_RUNTIME_ENVELOPE_FIELDS = frozenset({"contract_version", "operation", "payload"})
_SCOPE_FIELDS = frozenset({"tenant_id", "project_id", "project_revision"})


RuntimeOperationHandler = Callable[
    [Mapping[str, object], AuthorizationContext, int], object
]


@dataclass(frozen=True)
class SharedCoreOperation:
    """One host-bound operation in the allow-listed cross-client runtime ABI.

    The operation's API version, permission and payload field contract are
    declared centrally. The handler must call the existing typed Application/API
    service; it must not implement domain calculations or trust JSON identity.
    """

    contract_version: str
    permission: Permission
    required_fields: frozenset[str]
    allowed_fields: frozenset[str]
    handler: RuntimeOperationHandler

    def __post_init__(self) -> None:
        if not isinstance(self.contract_version, str) or not self.contract_version.strip():
            raise ValueError("RUNTIME_OPERATION_VERSION_REQUIRED")
        if not isinstance(self.permission, Permission):
            raise ValueError("RUNTIME_OPERATION_PERMISSION_REQUIRED")
        if not callable(self.handler):
            raise ValueError("RUNTIME_OPERATION_HANDLER_REQUIRED")
        required = frozenset(self.required_fields) | frozenset({"contract_version", "scope"})
        allowed = frozenset(self.allowed_fields) | required
        if not required.issubset(allowed):
            raise ValueError("RUNTIME_OPERATION_SCHEMA_INVALID")
        if "requested_by" in allowed or "authorization" in allowed or "roles" in allowed:
            raise ValueError("RUNTIME_OPERATION_MUST_NOT_ACCEPT_IDENTITY")
        object.__setattr__(self, "required_fields", required)
        object.__setattr__(self, "allowed_fields", allowed)


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
        allow_nan=False,
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"INVALID_JSON_CONSTANT:{value}")


def _schedule_request(payload: object) -> ScheduleQueryRequest:
    if not isinstance(payload, Mapping):
        raise ValueError("CORE_RUNTIME_PAYLOAD_INVALID")
    allowed = {
        "contract_version",
        "query_id",
        "scope",
        "requested_by",
        "query_text",
        "kind",
        "language",
        "constraints",
    }
    if set(payload) - allowed:
        raise ValueError("CORE_RUNTIME_UNKNOWN_PAYLOAD_FIELD")
    if payload.get("contract_version") != SCHEDULE_QUERY_VERSION:
        raise ValueError("UNSUPPORTED_SCHEDULE_QUERY_CONTRACT")

    required = ("query_id", "scope", "requested_by", "query_text", "kind", "language")
    if any(name not in payload for name in required):
        raise ValueError("CORE_RUNTIME_PAYLOAD_INVALID")
    if any(
        not isinstance(payload.get(name), str) or not payload.get(name).strip()
        for name in ("query_id", "requested_by", "query_text", "language", "kind")
    ):
        raise ValueError("CORE_RUNTIME_PAYLOAD_INVALID")

    raw_scope = payload.get("scope")
    if not isinstance(raw_scope, Mapping) or set(raw_scope) != _SCOPE_FIELDS:
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
    """Reusable Python runtime over authoritative Application APIs."""

    schedule_query_api: ScheduleQueryAPI
    authorization_policy: AuthorizationPolicy
    operations: Mapping[str, SharedCoreOperation] = field(default_factory=dict)

    def __post_init__(self) -> None:
        registry = dict(self.operations)
        for name, spec in registry.items():
            if (
                not isinstance(name, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", name)
                or name in {SCHEDULE_QUERY_OPERATION, "runtime.capabilities"}
            ):
                raise ValueError("INVALID_RUNTIME_OPERATION_NAME")
            if not isinstance(spec, SharedCoreOperation):
                raise ValueError("INVALID_RUNTIME_OPERATION_SPEC")
        object.__setattr__(self, "operations", MappingProxyType(registry))

    @property
    def supported_operations(self) -> tuple[dict[str, str], ...]:
        """Return the exact operation/version catalog for host capability checks."""
        entries = [
            {
                "operation": SCHEDULE_QUERY_OPERATION,
                "contract_version": SCHEDULE_QUERY_VERSION,
                "permission": Permission.PROJECT_READ.value,
            }
        ]
        entries.extend(
            {
                "operation": name,
                "contract_version": spec.contract_version,
                "permission": spec.permission.value,
            }
            for name, spec in sorted(self.operations.items())
        )
        return tuple(entries)

    def _validate_host(self, auth_context: AuthorizationContext, expected_project_revision: int) -> dict[str, object] | None:
        try:
            auth_context.validate()
        except AuthorizationError:
            return _error(
                "authorization",
                "INVALID_AUTHORIZATION_CONTEXT",
                "The host supplied an invalid authorization context.",
            )
        if (
            isinstance(expected_project_revision, bool)
            or not isinstance(expected_project_revision, int)
            or not 0 <= expected_project_revision <= MAX_SAFE_REVISION
        ):
            return _error(
                "authorization",
                "INVALID_HOST_PROJECT_REVISION",
                "The host supplied an invalid project revision.",
            )
        return None

    def execute_schedule_query(
        self,
        request: ScheduleQueryRequest,
        *,
        auth_context: AuthorizationContext,
        expected_project_revision: int,
    ) -> dict[str, object]:
        """Execute one query bound to host-authenticated identity and current revision."""
        invalid_host = self._validate_host(auth_context, expected_project_revision)
        if invalid_host is not None:
            return invalid_host
        if request.scope.project_revision != expected_project_revision:
            return _error(
                "conflict",
                "STALE_PROJECT_REVISION",
                "The request revision does not match the host's current project revision.",
            )
        if (
            request.scope.tenant_id != auth_context.tenant_id
            or request.scope.project_id != auth_context.project_id
        ):
            return _error(
                "authorization",
                "CROSS_SCOPE_ACCESS",
                "The requested project is outside the authenticated host scope.",
            )
        if request.requested_by != auth_context.user_id:
            return _error(
                "authorization",
                "REQUESTED_BY_MISMATCH",
                "The request actor does not match the authenticated host identity.",
            )
        return self.schedule_query_api.execute(request, auth_context=auth_context)

    @staticmethod
    def _runtime_exception(exc: Exception) -> dict[str, object]:
        if isinstance(exc, AuthorizationError):
            code = str(exc).strip()
            if code not in {"CROSS_SCOPE_ACCESS", "FORBIDDEN"}:
                code = "FORBIDDEN"
            return _error("authorization", code, "The authenticated actor is not allowed to perform this operation.")
        if isinstance(exc, (TypeError, ValueError, KeyError, ArithmeticError)):
            candidate = str(exc).split(":", 1)[0].strip()
            code = candidate if re.fullmatch(r"[A-Z][A-Z0-9_]{1,95}", candidate) else "INVALID_OPERATION_PAYLOAD"
            return _error("validation", code, "The operation payload or domain data was rejected.")
        return _error("internal", "RUNTIME_OPERATION_FAILED", "The operation could not be completed.")

    def _dispatch_registered_operation(
        self,
        operation: str,
        payload: object,
        *,
        auth_context: AuthorizationContext,
        expected_project_revision: int,
    ) -> dict[str, object]:
        spec = self.operations.get(operation)
        if spec is None:
            return _error(
                "validation",
                "UNSUPPORTED_CORE_RUNTIME_OPERATION",
                "The requested runtime operation is not registered by this host.",
            )
        if not isinstance(payload, Mapping):
            return _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The operation payload must be an object.")
        payload_data = dict(payload)
        mutation_metadata = payload_data.pop("mutation", None)
        if mutation_metadata is not None and (
            not spec.mutates or not isinstance(mutation_metadata, Mapping)
            or set(mutation_metadata) != {"mutation_id", "idempotency_key"}
            or any(
                not isinstance(mutation_metadata.get(name), str)
                or not mutation_metadata.get(name, "").strip()
                for name in ("mutation_id", "idempotency_key")
            )
        ):
            return _error("validation", "INVALID_MUTATION_ENVELOPE", "The mutation identity is invalid.")
        if spec.mutates and self.mutation_executor is not None and mutation_metadata is None:
            return _error("validation", "MUTATION_ENVELOPE_REQUIRED", "Offline writes require mutation and idempotency identifiers.")
        if set(payload_data) - spec.allowed_fields or not spec.required_fields.issubset(payload_data):
            return _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The operation payload fields do not match its versioned contract.")
        if payload_data.get("contract_version") != spec.contract_version:
            return _error("validation", "UNSUPPORTED_OPERATION_CONTRACT", "The operation contract version is not supported.")

        raw_scope = payload_data.get("scope")
        if not isinstance(raw_scope, Mapping) or set(raw_scope) != _SCOPE_FIELDS:
            return _error("validation", "CORE_RUNTIME_SCOPE_INVALID", "The project scope is invalid.")
        revision = raw_scope.get("project_revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or not 0 <= revision <= MAX_SAFE_REVISION:
            return _error("validation", "CORE_RUNTIME_SCOPE_INVALID", "The project revision is invalid.")
        if revision != expected_project_revision:
            return _error("conflict", "STALE_PROJECT_REVISION", "The request revision does not match the host's current project revision.")
        if (
            raw_scope.get("tenant_id") != auth_context.tenant_id
            or raw_scope.get("project_id") != auth_context.project_id
        ):
            return _error("authorization", "CROSS_SCOPE_ACCESS", "The requested project is outside the authenticated host scope.")

        invalid_host = self._validate_host(auth_context, expected_project_revision)
        if invalid_host is not None:
            return invalid_host
        if not self.authorization_policy.is_allowed(auth_context, spec.permission):
            return _error("authorization", "FORBIDDEN", "The authenticated actor is not allowed to perform this operation.")

        try:
            apply_operation = lambda: spec.handler(
                payload_data, auth_context, expected_project_revision
            )
            if spec.mutates and self.mutation_executor is not None:
                value = self.mutation_executor(
                    operation,
                    payload_data,
                    mutation_metadata,
                    auth_context,
                    expected_project_revision,
                    apply_operation,
                )
            else:
                value = apply_operation()
            if isinstance(value, Mapping):
                return dict(value)
            if isinstance(value, (tuple, list)):
                return {"items": list(value)}
            if value is None:
                return {"item": None}
            return {"value": value}
        except Exception as exc:  # noqa: BLE001 - stabilize all application errors at the ABI boundary.
            return self._runtime_exception(exc)

    def dispatch_json(
        self,
        request_json: str,
        *,
        auth_context: AuthorizationContext,
        expected_project_revision: int,
    ) -> str:
        """Dispatch JSON; identity, roles and current revision are host supplied."""
        if not isinstance(request_json, str) or len(request_json.encode("utf-8")) > MAX_RUNTIME_REQUEST_BYTES:
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The runtime request is missing or exceeds the size limit."),
            )
        try:
            envelope = json.loads(
                request_json,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The runtime request is not valid JSON."),
            )
        if not isinstance(envelope, Mapping) or set(envelope) != _RUNTIME_ENVELOPE_FIELDS:
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The runtime request envelope is invalid."),
            )
        if envelope.get("contract_version") != CORE_RUNTIME_CONTRACT_VERSION:
            return _response(
                "runtime.error",
                _error("validation", "UNSUPPORTED_CORE_RUNTIME_CONTRACT", "The runtime contract version is not supported."),
            )

        operation = envelope.get("operation")
        if not isinstance(operation, str) or not operation:
            return _response(
                "runtime.error",
                _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The runtime operation is invalid."),
            )
        if operation == SCHEDULE_QUERY_OPERATION:
            try:
                request = _schedule_request(envelope.get("payload"))
            except (KeyError, TypeError, ValueError):
                result = _error("validation", "CORE_RUNTIME_REQUEST_INVALID", "The schedule query payload is invalid.")
            else:
                result = self.execute_schedule_query(
                    request,
                    auth_context=auth_context,
                    expected_project_revision=expected_project_revision,
                )
            return _response(SCHEDULE_QUERY_OPERATION, result)

        result = self._dispatch_registered_operation(
            operation,
            envelope.get("payload"),
            auth_context=auth_context,
            expected_project_revision=expected_project_revision,
        )
        return _response(operation, result)


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
    operations: Mapping[str, SharedCoreOperation] | None = None,
) -> SharedCoreRuntime:
    """Compose the same Shared Core runtime for server or local hosts.

    The caller supplies authenticated host bindings and typed domain APIs. This
    function owns no database, network or UI, and does not duplicate calculations.
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
    return SharedCoreRuntime(
        schedule_query_api=schedule_query_api,
        authorization_policy=authorization_policy,
        operations={} if operations is None else operations,
    )


__all__ = [
    "CORE_RUNTIME_CONTRACT_VERSION",
    "MAX_RUNTIME_REQUEST_BYTES",
    "SCHEDULE_QUERY_OPERATION",
    "SharedCoreOperation",
    "SharedCoreRuntime",
    "build_shared_core_runtime",
]
