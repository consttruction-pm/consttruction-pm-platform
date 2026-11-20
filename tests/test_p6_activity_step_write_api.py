"""Activity step writes: create, edit, move, completion and delete."""

from __future__ import annotations

import contextlib
import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_step_api import (
    P6ActivityStepReadAPI,
    P6ActivityStepWriteAPI,
)
from construction_pm.p6_activity_step_repository import (
    P6ActivityStepApplicationService,
    P6ActivityStepPersistenceError,
    SQLiteP6ActivityStepRepository,
)

SCOPE = BackendScope("t1", "p1", 3)


class _NullTransactions:
    @staticmethod
    def transaction():
        return contextlib.nullcontext()


def build():
    service = P6ActivityStepApplicationService(
        SQLiteP6ActivityStepRepository(sqlite3.connect(":memory:")), _NullTransactions()
    )
    return (
        P6ActivityStepReadAPI(service, default_project_policy()),
        P6ActivityStepWriteAPI(service, default_project_policy()),
    )


def planner() -> AuthorizationContext:
    return AuthorizationContext("t1", "p1", "planner-1", frozenset({"planner"}))


def viewer() -> AuthorizationContext:
    return AuthorizationContext("t1", "p1", "viewer-1", frozenset({"viewer"}))


def test_create_edit_move_and_delete_round_trip() -> None:
    reader, writer = build()
    created = writer.create(
        SCOPE,
        "A130",
        description="Excavate",
        weight="40",
        percent_complete="25",
        sequence=None,
        auth_context=planner(),
    )["step"]
    assert created["sequence"] == 1
    assert created["percent_complete"] == "25"

    second = writer.create(
        SCOPE,
        "A130",
        description="Backfill",
        weight="60",
        percent_complete=None,
        sequence=None,
        auth_context=planner(),
    )["step"]
    assert second["sequence"] == 2

    updated = writer.update(
        SCOPE,
        "A130",
        second["step_id"],
        description="Backfill and compact",
        weight="60",
        percent_complete="50",
        sequence=3,
        auth_context=planner(),
    )["step"]
    assert updated["description"] == "Backfill and compact"
    assert updated["sequence"] == 3
    assert updated["percent_complete"] == "50"

    listed = reader.list(SCOPE, "A130", auth_context=viewer())["steps"]
    assert [(item["step_id"], item["percent_complete"]) for item in listed] == [
        (created["step_id"], "25"),
        (second["step_id"], "50"),
    ]

    assert writer.delete(SCOPE, "A130", created["step_id"], auth_context=planner())["deleted"] is True
    assert [item["step_id"] for item in reader.list(SCOPE, "A130", auth_context=viewer())["steps"]] == [second["step_id"]]


def test_write_requires_project_write_permission() -> None:
    _, writer = build()
    with pytest.raises(AuthorizationError):
        writer.create(
            SCOPE,
            "A130",
            description="x",
            weight=None,
            percent_complete=None,
            sequence=None,
            auth_context=viewer(),
        )


def test_step_from_another_activity_is_not_editable() -> None:
    _, writer = build()
    created = writer.create(
        SCOPE,
        "A130",
        description="Excavate",
        weight=None,
        percent_complete=None,
        sequence=None,
        auth_context=planner(),
    )["step"]
    with pytest.raises(P6ActivityStepPersistenceError, match="ACTIVITY_STEP_NOT_FOUND"):
        writer.update(
            SCOPE,
            "A140",
            created["step_id"],
            description="Wrong activity",
            weight=None,
            percent_complete=None,
            sequence=None,
            auth_context=planner(),
        )


def test_invalid_percent_and_weight_fail_closed() -> None:
    _, writer = build()
    with pytest.raises(P6ActivityStepPersistenceError, match="INVALID_PERCENT_COMPLETE"):
        writer.create(
            SCOPE,
            "A130",
            description="x",
            weight=None,
            percent_complete="120",
            sequence=None,
            auth_context=planner(),
        )
    with pytest.raises(P6ActivityStepPersistenceError, match="INVALID_WEIGHT"):
        writer.create(
            SCOPE,
            "A130",
            description="x",
            weight="heavy",
            percent_complete=None,
            sequence=None,
            auth_context=planner(),
        )
