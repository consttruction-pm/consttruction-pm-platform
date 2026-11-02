from __future__ import annotations

import sqlite3
from datetime import date
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.constraint_master_repository import (
    ConstraintMaster,
    ConstraintPersistenceError,
    SQLiteConstraintMasterRepository,
)
from construction_pm.p6_constraint_api import P6_CONSTRAINT_API_VERSION, P6ConstraintAPI
from construction_pm.scheduling.constraints import ConstraintType


class ActivityLookup:
    def __init__(self, ids=("A1",)):
        self.ids = set(ids)

    def get(self, scope, activity_id):
        return SimpleNamespace(activity_id=activity_id) if activity_id in self.ids else None


def scope(revision=4):
    return BackendScope("tenant-a", "project-a", revision)


def auth(role="project_admin", tenant="tenant-a", project="project-a"):
    return AuthorizationContext(tenant, project, "user-a", frozenset({role}))


def item(constraint_id="C-1", kind=ConstraintType.START_NO_EARLIER_THAN):
    return ConstraintMaster(
        scope=scope(),
        constraint_id=constraint_id,
        activity_id="A1",
        constraint_type=kind,
        constraint_date=date(2026, 11, 3),
    )


def api(connection):
    return P6ConstraintAPI(
        SQLiteConstraintMasterRepository(connection),
        ActivityLookup(),
        default_project_policy(),
    )


def test_constraint_api_create_update_read_and_list_are_typed_and_revision_bound():
    connection = sqlite3.connect(":memory:")
    boundary = api(connection)
    created = boundary.create(item(), auth_context=auth())
    assert created["contract_version"] == P6_CONSTRAINT_API_VERSION
    assert created["constraint"]["record_revision"] == 1
    assert boundary.get(scope(), "C-1", auth_context=auth()) == created
    assert boundary.list(scope(), auth_context=auth()) == (created,)

    updated = boundary.update(
        item(kind=ConstraintType.MANDATORY_FINISH),
        expected_revision=1,
        auth_context=auth(),
    )
    assert updated["constraint"]["record_revision"] == 2
    assert updated["constraint"]["constraint_type"] == "MANDATORY_FINISH"

    with pytest.raises(ConstraintPersistenceError, match="REVISION_CONFLICT"):
        boundary.update(item(), expected_revision=1, auth_context=auth())
    connection.close()


def test_constraint_api_fails_closed_for_scope_permission_and_unknown_activity():
    connection = sqlite3.connect(":memory:")
    boundary = api(connection)
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        boundary.create(item(), auth_context=auth(tenant="other"))
    with pytest.raises(AuthorizationError, match="authorization denied"):
        boundary.list(scope(), auth_context=auth(role="viewer"))

    no_activity = P6ConstraintAPI(
        SQLiteConstraintMasterRepository(sqlite3.connect(":memory:")),
        ActivityLookup(ids=()),
        default_project_policy(),
    )
    with pytest.raises(ValueError, match="CONSTRAINT_ACTIVITY_NOT_FOUND"):
        no_activity.create(item(), auth_context=auth())
    connection.close()


def test_sqlite_constraint_repository_never_commits_caller_owned_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE caller_state (value TEXT NOT NULL)")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO caller_state(value) VALUES ('pending')")
    repository = SQLiteConstraintMasterRepository(connection)
    assert connection.in_transaction
    repository.save(item(), expected_revision=0)
    assert connection.in_transaction
    connection.rollback()
    assert connection.execute("SELECT value FROM caller_state").fetchall() == []
    assert repository.get(scope(), "C-1") is None
    connection.close()


def test_sqlite_constraint_repository_schema_initialization_respects_outer_transaction():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE caller_state (value TEXT NOT NULL)")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO caller_state(value) VALUES ('pending')")
    SQLiteConstraintMasterRepository(connection)
    assert connection.in_transaction
    connection.rollback()
    assert connection.execute("SELECT value FROM caller_state").fetchall() == []
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='constraint_master'"
    ).fetchone() is None
    connection.close()
