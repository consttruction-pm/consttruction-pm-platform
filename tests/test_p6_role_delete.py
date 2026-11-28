import sqlite3

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_role_api import P6RoleAPI
from construction_pm.p6_role_dictionary_repository import (
    P6RoleLimit,
    P6RoleRate,
    P6RoleResource,
    SQLiteP6RoleDictionaryRepository,
)
from construction_pm.p6_role_repository import (
    P6Role,
    RoleInUseError,
    SQLiteP6RoleRepository,
)


def auth(tenant="t1", project="p1", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def make_role(role_id="role-1", project="p1", revision=0):
    return P6Role("t1", project, 2, role_id, "Site Engineer", "Engineering role", revision)


def build(connection=None):
    connection = connection or sqlite3.connect(":memory:")
    roles = SQLiteP6RoleRepository(connection)
    dictionary = SQLiteP6RoleDictionaryRepository(connection)
    assignments = SQLiteP6ResourceAssignmentRepository(connection)
    service = P6RoleAPI(roles, default_project_policy())
    return connection, roles, dictionary, assignments, service


def seed_owned_facts(dictionary, role_id="role-1"):
    dictionary.save_rate(P6RoleRate("t1", "p1", 2, role_id, "2026-01-01", "standard", "100.00", "h", "USD", "test"))
    dictionary.save_limit(P6RoleLimit("t1", "p1", 2, role_id, "2026-01-01", "40", "units"))
    dictionary.save_role_resource(P6RoleResource("t1", "p1", 2, role_id, "RES-A", "skilled", True))


def seed_assignment(assignments, role_id="role-1", project="p1", assignment_id="A1"):
    assignments.upsert(
        P6ResourceAssignment(
            BackendScope("t1", project, 2),
            assignment_id,
            "ACT-1",
            "RES-A",
            role_id=role_id,
        )
    )


def test_delete_unreferenced_role_removes_owned_facts_and_reports_rows():
    connection, roles, dictionary, _assignments, service = build()
    roles.save(make_role())
    seed_owned_facts(dictionary)

    result = service.delete("t1", "p1", 2, "role-1", expected_revision=1, auth_context=auth())

    assert result["kind"] == "p6_role_deleted"
    assert result["role_id"] == "role-1"
    assert result["deleted"] is True
    assert result["removed_rows"]["p6_role"] == 1
    assert result["removed_rows"]["rate_facts"] == 1
    assert result["removed_rows"]["limits"] == 1
    assert result["removed_rows"]["role_resource_links"] == 1
    assert roles.get("t1", "p1", 2, "role-1") is None
    assert dictionary.list_rates("t1", "p1", 2, "role-1") == ()
    assert dictionary.list_limits("t1", "p1", 2, "role-1") == ()
    assert dictionary.list_role_resources("t1", "p1", 2, "role-1") == ()


def test_delete_refuses_when_an_assignment_references_the_role():
    _connection, roles, dictionary, assignments, service = build()
    roles.save(make_role())
    seed_owned_facts(dictionary)
    seed_assignment(assignments)

    with pytest.raises(RoleInUseError) as excinfo:
        service.delete("t1", "p1", 2, "role-1", expected_revision=1, auth_context=auth())

    assert excinfo.value.dependencies == {"assignments": 1}
    # Nothing is deleted when the delete is refused.
    assert roles.get("t1", "p1", 2, "role-1") is not None
    assert len(dictionary.list_rates("t1", "p1", 2, "role-1")) == 1


def test_delete_refuses_when_a_child_role_depends_on_it():
    _connection, roles, _dictionary, _assignments, service = build()
    roles.save(make_role("parent"))
    roles.save(P6Role("t1", "p1", 2, "child", "Child", None, 0, "parent"))

    with pytest.raises(RoleInUseError) as excinfo:
        service.delete("t1", "p1", 2, "parent", expected_revision=1, auth_context=auth())

    assert excinfo.value.dependencies == {"child_roles": 1}
    assert roles.get("t1", "p1", 2, "parent") is not None


def test_delete_requires_scope_revision_and_write_permission():
    _connection, roles, _dictionary, _assignments, service = build()
    roles.save(make_role())

    with pytest.raises(ValueError, match="ROLE_NOT_FOUND"):
        service.delete("t1", "p1", 2, "missing", expected_revision=1, auth_context=auth())
    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        service.delete("t1", "p1", 2, "role-1", expected_revision=9, auth_context=auth())
    with pytest.raises(ValueError, match="ROLE_REVISION_REQUIRED"):
        service.delete("t1", "p1", 2, "role-1", expected_revision=0, auth_context=auth())
    with pytest.raises(AuthorizationError):
        service.delete("t1", "p1", 2, "role-1", expected_revision=1, auth_context=auth(roles=("viewer",)))
    with pytest.raises(AuthorizationError, match="CROSS_SCOPE_ACCESS"):
        service.delete("t1", "p2", 2, "role-1", expected_revision=1, auth_context=auth())
    assert roles.get("t1", "p1", 2, "role-1") is not None


def test_delete_is_isolated_across_projects_and_ignores_other_project_assignments():
    connection, roles, dictionary, assignments, service = build()
    roles.save(make_role("role-1", project="p1"))
    # A same-named role with an assignment in another project must not block
    # deletion in this project, and the other project's role is untouched.
    roles.save(make_role("role-1", project="p2"))
    seed_assignment(assignments, project="p2", assignment_id="A2")

    result = service.delete("t1", "p1", 2, "role-1", expected_revision=1, auth_context=auth(project="p1"))

    assert result["deleted"] is True
    assert roles.get("t1", "p1", 2, "role-1") is None
    assert roles.get("t1", "p2", 2, "role-1") is not None
    assert len(assignments.list(BackendScope("t1", "p2", 2))) == 1