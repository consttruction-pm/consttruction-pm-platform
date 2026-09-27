from __future__ import annotations

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.errors import ErrorCategory
from construction_pm.backend_p0.schedule_query import (
    SCHEDULE_QUERY_RESULT_VERSION,
    ScheduleQueryAPI,
    ScheduleQueryApplicationService,
)
from construction_pm.control_intelligence.contracts import ControlScope, SourceReference
from construction_pm.control_intelligence.query import ScheduleQueryAnswer, ScheduleQueryRequest


def policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(
        {
            "viewer": frozenset({Permission.PROJECT_READ}),
            "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        }
    )


def auth(
    tenant_id: str = "tenant-1",
    project_id: str = "project-1",
    role: str = "viewer",
) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id,
        project_id,
        "user-1",
        frozenset({role}),
    )


def request() -> ScheduleQueryRequest:
    return ScheduleQueryRequest(
        "Q-1",
        ControlScope("tenant-1", "project-1", 7),
        "user-1",
        "Which activities are at risk?",
    )


class Provider:
    def __init__(self, answer: ScheduleQueryAnswer) -> None:
        self.answer = answer
        self.requests: list[ScheduleQueryRequest] = []

    def execute(self, request: ScheduleQueryRequest) -> ScheduleQueryAnswer:
        self.requests.append(request)
        return self.answer


def answer(
    *,
    query_id: str = "Q-1",
    scope: ControlScope | None = None,
) -> ScheduleQueryAnswer:
    return ScheduleQueryAnswer(
        query_id,
        scope or ControlScope("tenant-1", "project-1", 7),
        "schedule.query.result",
        data={"count": 2},
        source_refs=(
            SourceReference("S-1", "schedule", "/schedule/A-1", 7),
        ),
    )


def test_application_delegates_to_provider_and_preserves_scope() -> None:
    provider = Provider(answer())
    service = ScheduleQueryApplicationService(provider, policy())

    result = service.execute(request(), auth_context=auth())

    assert result.query_id == "Q-1"
    assert result.scope == request().scope
    assert provider.requests == [request()]


def test_application_rejects_cross_scope_and_forbidden_reads() -> None:
    service = ScheduleQueryApplicationService(Provider(answer()), policy())

    try:
        service.execute(request(), auth_context=auth(tenant_id="tenant-2"))
    except Exception as exc:
        assert getattr(exc, "category") == ErrorCategory.AUTHORIZATION
        assert getattr(exc, "code") == "CROSS_SCOPE_ACCESS"
    else:
        pytest.fail("cross-scope query was accepted")

    try:
        service.execute(request(), auth_context=auth(role="unknown-role"))
    except Exception as exc:
        assert getattr(exc, "category") == ErrorCategory.AUTHORIZATION
        assert getattr(exc, "code") == "FORBIDDEN"
    else:
        pytest.fail("forbidden query was accepted")


@pytest.mark.parametrize(
    "bad_answer, error",
    [
        (answer(query_id="Q-2"), "SCHEDULE_QUERY_RESULT_ID_MISMATCH"),
        (
            answer(scope=ControlScope("tenant-1", "project-1", 8)),
            "SCHEDULE_QUERY_RESULT_SCOPE_MISMATCH",
        ),
    ],
)
def test_application_rejects_provider_result_mismatch(
    bad_answer: ScheduleQueryAnswer,
    error: str,
) -> None:
    service = ScheduleQueryApplicationService(Provider(bad_answer), policy())

    try:
        service.execute(request(), auth_context=auth())
    except Exception as exc:
        assert getattr(exc, "category") == ErrorCategory.CONFLICT
        assert getattr(exc, "code") == error
    else:
        pytest.fail(f"provider mismatch was accepted: {error}")


def test_api_returns_versioned_source_backed_result() -> None:
    api = ScheduleQueryAPI(
        ScheduleQueryApplicationService(Provider(answer()), policy())
    )

    result = api.execute(request(), auth_context=auth())

    assert result["contract_version"] == SCHEDULE_QUERY_RESULT_VERSION
    assert result["query_id"] == "Q-1"
    assert result["scope"]["project_revision"] == 7
    assert result["data"] == {"count": 2}
    assert result["source_refs"][0]["source_id"] == "S-1"


def test_api_maps_authorization_and_validation_errors() -> None:
    api = ScheduleQueryAPI(
        ScheduleQueryApplicationService(Provider(answer()), policy())
    )

    forbidden = api.execute(
        request(),
        auth_context=auth(role="unknown-role"),
    )
    assert forbidden["error"]["code"] == "FORBIDDEN"
    assert forbidden["error"]["category"] == ErrorCategory.AUTHORIZATION.value

    class InvalidProvider:
        def execute(self, request: ScheduleQueryRequest) -> ScheduleQueryAnswer:
            return object()  # type: ignore[return-value]

    invalid = ScheduleQueryAPI(
        ScheduleQueryApplicationService(InvalidProvider(), policy())
    ).execute(request(), auth_context=auth())
    assert invalid["error"]["code"] == "INVALID_SCHEDULE_QUERY_RESULT"
    assert invalid["error"]["category"] == ErrorCategory.VALIDATION.value
