import sqlite3

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, default_project_policy
from construction_pm.p6_role_api import P6_ROLE_API_VERSION, P6RoleAPI
from construction_pm.p6_role_repository import P6Role, SQLiteP6RoleRepository


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def role(revision=0, name="Site Engineer"):
    return P6Role("t1", "p1", 2, "role-1", name, "Engineering role", revision)


def api(connection):
    return P6RoleAPI(SQLiteP6RoleRepository(connection), default_project_policy())


def test_p6_role_api_round_trip_and_registry_identity():
    service = api(sqlite3.connect(":memory:"))
    created = service.create(role(), auth_context=auth())
    assert created["contract_version"] == P6_ROLE_API_VERSION
    assert created["kind"] == "p6_role"
    assert created["role"]["role_id"] == "role-1"
    assert created["role"]["record_revision"] == 1
    assert service.get("t1", "p1", 2, "role-1", auth_context=auth()) == created
    assert service.list("t1", "p1", 2, auth_context=auth()) == (created,)


def test_p6_role_api_enforces_scope_and_write_permission():
    service = api(sqlite3.connect(":memory:"))
    service.create(role(), auth_context=auth())
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.get("other", "p1", 2, "role-1", auth_context=auth())
    with pytest.raises(AuthorizationError):
        service.create(role(), auth_context=auth(roles=("viewer",)))


def test_p6_role_api_uses_optimistic_record_revision():
    service = api(sqlite3.connect(":memory:"))
    service.create(role(), auth_context=auth())
    updated = service.update(role(revision=1, name="Senior Site Engineer"), expected_revision=1, auth_context=auth())
    assert updated["role"]["record_revision"] == 2
    assert updated["role"]["name"] == "Senior Site Engineer"
    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        service.update(role(revision=2, name="Stale"), expected_revision=1, auth_context=auth())
