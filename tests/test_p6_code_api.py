from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_code_api import (
    P6_CODE_API_VERSION,
    P6_CODE_ASSIGNMENT_API_VERSION,
    P6CodeAPI,
    P6CodeAssignmentAPI,
)
from construction_pm.p6_code_assignment_repository import (
    P6CodeAssignment,
    P6CodeAssignmentApplicationService,
    SQLiteP6CodeAssignmentRepository,
)
from construction_pm.p6_code_repository import (
    P6CodeApplicationService,
    P6CodeDefinition,
    P6CodeValue,
    SQLiteP6CodeRepository,
)


class TransactionManager:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def scope(revision: int = 7) -> BackendScope:
    return BackendScope("t1", "p1", revision)


def auth(*, tenant_id: str = "t1", project_id: str = "p1", role: str = "planner") -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="u1",
        roles=frozenset({role}),
    )


def code() -> P6CodeDefinition:
    return P6CodeDefinition(
        scope=scope(),
        code_id="ACTIVITY_STATUS",
        name="Activity Status",
        subject_area="ACTIVITY",
        scope_kind="PROJECT",
        scope_key="p1",
        values=(
            P6CodeValue("NOT_STARTED", "Not Started"),
            P6CodeValue("IN_PROGRESS", "In Progress", "Work started"),
        ),
    )


def assignment() -> P6CodeAssignment:
    return P6CodeAssignment(
        scope=scope(),
        code_id="ACTIVITY_STATUS",
        value_id="IN_PROGRESS",
        owner_type="ACTIVITY",
        owner_id="A1",
        metadata="source=p6",
    )


def apis() -> tuple[P6CodeAPI, P6CodeAssignmentAPI]:
    connection = sqlite3.connect(":memory:")
    code_repo = SQLiteP6CodeRepository(connection)
    assignment_repo = SQLiteP6CodeAssignmentRepository(connection)
    manager = TransactionManager(connection)
    return (
        P6CodeAPI(P6CodeApplicationService(code_repo, manager), default_project_policy()),
        P6CodeAssignmentAPI(
            P6CodeAssignmentApplicationService(assignment_repo, manager),
            default_project_policy(),
        ),
    )


def test_versioned_typed_code_and_assignment_round_trip() -> None:
    code_api, assignment_api = apis()

    created_code = code_api.create(code(), auth_context=auth())
    assert created_code["contract_version"] == P6_CODE_API_VERSION
    assert created_code["kind"] == "p6_code"
    assert created_code["scope"]["project_revision"] == 7
    assert [item["value_id"] for item in created_code["code"]["values"]] == [
        "NOT_STARTED",
        "IN_PROGRESS",
    ]
    assert code_api.get(scope(), "ACTIVITY_STATUS", auth_context=auth()) == created_code
    assert code_api.list(scope(), subject_area="ACTIVITY", auth_context=auth()) == (created_code,)

    created_assignment = assignment_api.create(assignment(), auth_context=auth())
    assert created_assignment["contract_version"] == P6_CODE_ASSIGNMENT_API_VERSION
    assert created_assignment["kind"] == "p6_code_assignment"
    assert created_assignment["assignment"]["metadata"] == "source=p6"
    assert assignment_api.get(
        scope(), "ACTIVITY_STATUS", "IN_PROGRESS", "ACTIVITY", "A1", auth_context=auth()
    ) == created_assignment
    assert assignment_api.list(scope(), owner_type="ACTIVITY", owner_id="A1", auth_context=auth()) == (
        created_assignment,
    )


def test_code_and_assignment_apis_reject_cross_scope_and_read_without_permission() -> None:
    code_api, assignment_api = apis()

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        code_api.create(code(), auth_context=auth(tenant_id="other"))

    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        assignment_api.create(assignment(), auth_context=auth(project_id="other"))

    with pytest.raises(AuthorizationError, match="authorization denied"):
        code_api.get(scope(), "ACTIVITY_STATUS", auth_context=auth(role="writer"))

    with pytest.raises(AuthorizationError, match="authorization denied"):
        assignment_api.get(
            scope(), "ACTIVITY_STATUS", "IN_PROGRESS", "ACTIVITY", "A1", auth_context=auth(role="writer")
        )


class SecureCodePolicy:
    def __init__(self, allowed_actions):
        self.allowed_actions = set(allowed_actions)

    def is_allowed(self, context, permission):
        return True

    def allows_secure_code_action(self, context, action):
        return action in self.allowed_actions


def test_secure_code_definition_is_persisted_and_hidden_without_view_privilege():
    connection = sqlite3.connect(":memory:")
    manager = TransactionManager(connection)
    code_service = P6CodeApplicationService(SQLiteP6CodeRepository(connection), manager)
    admin_api = P6CodeAPI(code_service, SecureCodePolicy({"view", "add_delete"}))
    secure_definition = __import__("dataclasses").replace(code(), is_secure=True)
    created = admin_api.create(secure_definition, auth_context=auth())
    assert created["code"]["is_secure"] is True

    reader_api = P6CodeAPI(code_service, SecureCodePolicy(set()))
    assert reader_api.get(scope(), "ACTIVITY_STATUS", auth_context=auth()) is None
    assert reader_api.list(scope(), subject_area="ACTIVITY", auth_context=auth()) == ()
    with pytest.raises(AuthorizationError, match="SECURE_CODE_ADD_DELETE_NOT_AUTHORIZED"):
        reader_api.create(
            __import__("dataclasses").replace(code(), code_id="SECURE-OTHER", is_secure=True),
            auth_context=auth(),
        )


def test_secure_code_assignment_requires_assign_and_view_privileges():
    connection = sqlite3.connect(":memory:")
    manager = TransactionManager(connection)
    code_service = P6CodeApplicationService(SQLiteP6CodeRepository(connection), manager)
    assignment_service = P6CodeAssignmentApplicationService(
        SQLiteP6CodeAssignmentRepository(connection), manager
    )
    definition = __import__("dataclasses").replace(code(), is_secure=True)
    code_service.save(definition)

    admin_api = P6CodeAssignmentAPI(
        assignment_service, SecureCodePolicy({"assign", "view"}), code_service=code_service
    )
    admin_api.create(assignment(), auth_context=auth())

    reader_api = P6CodeAssignmentAPI(
        assignment_service, SecureCodePolicy(set()), code_service=code_service
    )
    assert reader_api.get(
        scope(), "ACTIVITY_STATUS", "IN_PROGRESS", "ACTIVITY", "A1", auth_context=auth()
    ) is None
    assert reader_api.list(scope(), auth_context=auth()) == ()

    viewer_only = P6CodeAssignmentAPI(
        assignment_service, SecureCodePolicy({"view"}), code_service=code_service
    )
    with pytest.raises(AuthorizationError, match="SECURE_CODE_ASSIGN_NOT_AUTHORIZED"):
        viewer_only.create(
            P6CodeAssignment(scope(), "ACTIVITY_STATUS", "NOT_STARTED", "ACTIVITY", "A2"),
            auth_context=auth(),
        )


def test_secure_code_assignment_policy_fails_closed_without_definition_lookup():
    connection = sqlite3.connect(":memory:")
    manager = TransactionManager(connection)
    service = P6CodeAssignmentApplicationService(
        SQLiteP6CodeAssignmentRepository(connection), manager
    )
    restricted = P6CodeAssignmentAPI(service, SecureCodePolicy({"assign", "view"}))
    with pytest.raises(AuthorizationError, match="SECURE_CODE_DEFINITION_LOOKUP_REQUIRED"):
        restricted.create(assignment(), auth_context=auth())
