from __future__ import annotations

import contextlib
import sqlite3
from decimal import Decimal

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_step_api import (
    P6_ACTIVITY_STEP_READ_API_VERSION,
    P6ActivityStepReadAPI,
)
from construction_pm.p6_activity_step_repository import (
    P6ActivityStep,
    P6ActivityStepApplicationService,
    P6ActivityStepPersistenceError,
    SQLiteP6ActivityStepRepository,
)

SCOPE = BackendScope("t1", "p1", 3)


class _NullTransactions:
    @staticmethod
    def transaction():
        return contextlib.nullcontext()


def api() -> P6ActivityStepReadAPI:
    repository = SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:"))
    return P6ActivityStepReadAPI(
        P6ActivityStepApplicationService(repository, _NullTransactions()),
        default_project_policy(),
    )


def viewer() -> AuthorizationContext:
    return AuthorizationContext("t1", "p1", "viewer-1", frozenset({"viewer"}))


def viewer_for(tenant_id: str, project_id: str) -> AuthorizationContext:
    return AuthorizationContext(tenant_id, project_id, "viewer-1", frozenset({"viewer"}))


def step(step_id: str, sequence: int, **overrides) -> P6ActivityStep:
    payload = {
        "scope": SCOPE,
        "step_id": step_id,
        "activity_id": "A130",
        "sequence": sequence,
        "description": f"Step {sequence}",
        "weight": Decimal("25"),
        "udf_values": (("crew", "C-01"),),
    }
    payload.update(overrides)
    return P6ActivityStep(**payload)  # type: ignore[arg-type]


def seed(api_: P6ActivityStepReadAPI) -> None:
    for item in (step("S2", 2), step("S1", 1)):
        api_.service.save(item)


def test_list_returns_stored_steps_in_sequence_order() -> None:
    service = api()
    seed(service)
    result = service.list(SCOPE, "A130", auth_context=viewer())
    assert result["contract_version"] == P6_ACTIVITY_STEP_READ_API_VERSION
    assert result["kind"] == "p6_activity_step_list"
    assert result["activity_id"] == "A130"
    assert [item["step_id"] for item in result["steps"]] == ["S1", "S2"]
    first = result["steps"][0]
    assert first["weight"] == "25"
    assert first["udf_values"] == {"crew": "C-01"}
    assert "percent_complete" not in first


def test_empty_collection_is_an_explicit_empty_list() -> None:
    result = api().list(SCOPE, "A130", auth_context=viewer())
    assert result["steps"] == []


def test_steps_are_isolated_by_tenant_project_and_activity() -> None:
    service = api()
    seed(service)
    service.service.save(step("S9", 1, activity_id="A999"))
    assert service.list(SCOPE, "A999", auth_context=viewer())["steps"][0]["step_id"] == "S9"
    other_tenant = BackendScope("t2", "p1", 3)
    other_project = BackendScope("t1", "p2", 3)
    assert service.list(other_tenant, "A130", auth_context=viewer_for("t2", "p1"))["steps"] == []
    assert service.list(other_project, "A130", auth_context=viewer_for("t1", "p2"))["steps"] == []


def test_cross_scope_authorization_is_rejected() -> None:
    service = api()
    with pytest.raises(AuthorizationError):
        service.list(BackendScope("t2", "p1", 3), "A130", auth_context=viewer())


def test_read_requires_project_read_permission() -> None:
    with pytest.raises(AuthorizationError):
        api().list(
            SCOPE,
            "A130",
            auth_context=AuthorizationContext("t1", "p1", "nobody", frozenset()),
        )


def test_stale_revision_fails_closed() -> None:
    service = api()
    seed(service)
    with pytest.raises(P6ActivityStepPersistenceError, match="REVISION_CONFLICT"):
        service.list(BackendScope("t1", "p1", 4), "A130", auth_context=viewer())


def test_invalid_activity_id_is_rejected() -> None:
    service = api()
    with pytest.raises(P6ActivityStepPersistenceError, match="INVALID_ACTIVITY_ID"):
        service.list(SCOPE, "   ", auth_context=viewer())
