"""Live PostgreSQL acceptance for the P6 role delete.

Creates a throw-away schema, then drives the same ``P6RoleAPI`` and
``PostgresP6RoleRepository`` the runtime composes. Proves:
- an unreferenced role is deleted and its role-owned rate/limit/resource-link
  facts go with it (no orphan),
- a role referenced by a live assignment (or a child role) is refused with
  per-reference counts and nothing is committed,
- tenant/project scope and the record-revision guard are enforced,
- a same-id role in another project or tenant is untouched.
"""

from __future__ import annotations

from contextlib import contextmanager
import os
import uuid

import pytest

if not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") and os.getenv("P6_TEST_POSTGRES_DSN"):
    os.environ["CONSTRUCTION_PM_POSTGRES_DSN"] = os.environ["P6_TEST_POSTGRES_DSN"]

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

from construction_pm.application.authorization import (  # noqa: E402
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.p6_resource_assignment_repository import (  # noqa: E402
    PostgresP6ResourceAssignmentRepository,
)
from construction_pm.p6_role_api import P6RoleAPI  # noqa: E402
from construction_pm.p6_role_repository import (  # noqa: E402
    P6Role,
    PostgresP6RoleRepository,
    RoleInUseError,
)


class _Tx:
    def __init__(self, connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise


def auth(tenant="tenant-live", project="project-live", roles=("planner",)):
    return AuthorizationContext(tenant, project, "u1", frozenset(roles))


def _connect():
    import psycopg

    schema = f"cubi_rol_{uuid.uuid4().hex[:12]}"
    connection = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={schema}",
    )
    connection.execute(f'CREATE SCHEMA "{schema}"')
    connection.autocommit = False
    return connection, schema


def _create_owned_tables(connection) -> None:
    """The role dictionary is SQLite-only today; create its tables to prove the
    Postgres delete removes role-owned facts when they exist."""
    connection.execute(
        "CREATE TABLE IF NOT EXISTS p6_role_rate ("
        "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL,"
        "role_id TEXT NOT NULL, effective_from TEXT NOT NULL, rate_type TEXT NOT NULL,"
        "rate TEXT NOT NULL, unit TEXT NOT NULL, currency TEXT NOT NULL, source TEXT NOT NULL,"
        "record_revision BIGINT NOT NULL DEFAULT 0,"
        "PRIMARY KEY (tenant_id, project_id, role_id, effective_from, rate_type))"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS p6_role_limit ("
        "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL,"
        "role_id TEXT NOT NULL, effective_from TEXT NOT NULL, max_units TEXT NOT NULL,"
        "unit_basis TEXT NOT NULL, record_revision BIGINT NOT NULL DEFAULT 0,"
        "PRIMARY KEY (tenant_id, project_id, role_id, effective_from))"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS p6_role_resource ("
        "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision BIGINT NOT NULL,"
        "role_id TEXT NOT NULL, resource_id TEXT NOT NULL, proficiency TEXT NOT NULL,"
        "is_primary BOOLEAN NOT NULL DEFAULT FALSE, record_revision BIGINT NOT NULL DEFAULT 0,"
        "PRIMARY KEY (tenant_id, project_id, role_id, resource_id))"
    )


@pytest.fixture()
def live():
    connection, schema = _connect()
    try:
        PostgresP6RoleRepository(connection).initialize()
        PostgresP6ResourceAssignmentRepository(connection).initialize()
        _create_owned_tables(connection)
        connection.commit()
        yield connection, P6RoleAPI(PostgresP6RoleRepository(connection), default_project_policy())
    finally:
        connection.rollback()
        connection.autocommit = True
        connection.execute("SET search_path TO public")
        connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
        connection.close()


def _role(role_id="ROLE-1", *, tenant="tenant-live", project="project-live", parent=None):
    return P6Role(tenant, project, 1, role_id, "Site Engineer", "Engineering role", 0, parent)


def _create(connection, api, role):
    with _Tx(connection).transaction():
        return api.create(role, auth_context=auth(role.tenant_id, role.project_id))


def test_live_role_delete_removes_role_owned_facts(live):
    connection, api = live
    _create(connection, api, _role())
    connection.execute(
        "INSERT INTO p6_role_rate VALUES "
        "('tenant-live','project-live',1,'ROLE-1','2026-01-01','standard','100.00','h','USD','manual',1)"
    )
    connection.execute(
        "INSERT INTO p6_role_limit VALUES "
        "('tenant-live','project-live',1,'ROLE-1','2026-01-01','40','units',1)"
    )
    connection.execute(
        "INSERT INTO p6_role_resource VALUES "
        "('tenant-live','project-live',1,'ROLE-1','RES-A','skilled',TRUE,1)"
    )
    connection.commit()

    with _Tx(connection).transaction():
        result = api.delete(
            "tenant-live", "project-live", 1, "ROLE-1",
            expected_revision=1, auth_context=auth(),
        )

    assert result["deleted"] is True
    assert result["removed_rows"]["p6_role"] == 1
    assert result["removed_rows"]["rate_facts"] == 1
    assert result["removed_rows"]["limits"] == 1
    assert result["removed_rows"]["role_resource_links"] == 1
    assert api.get("tenant-live", "project-live", 1, "ROLE-1", auth_context=auth()) is None
    for table in ("p6_role_rate", "p6_role_limit", "p6_role_resource"):
        assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_live_role_delete_refuses_a_live_assignment_and_commits_nothing(live):
    connection, api = live
    _create(connection, api, _role())
    connection.execute(
        "INSERT INTO p6_resource_assignment "
        "(tenant_id,project_id,project_revision,assignment_id,activity_id,resource_id,role_id) "
        "VALUES ('tenant-live','project-live',1,'ASN-1','A-1','RES-A','ROLE-1')"
    )
    connection.commit()

    with pytest.raises(RoleInUseError) as blocked:
        with _Tx(connection).transaction():
            api.delete(
                "tenant-live", "project-live", 1, "ROLE-1",
                expected_revision=1, auth_context=auth(),
            )
    assert blocked.value.dependencies["assignments"] == 1
    assert api.get("tenant-live", "project-live", 1, "ROLE-1", auth_context=auth()) is not None
    assert connection.execute("SELECT COUNT(*) FROM p6_resource_assignment").fetchone()[0] == 1


def test_live_role_delete_refuses_a_child_role(live):
    connection, api = live
    _create(connection, api, _role("ROLE-P"))
    _create(connection, api, _role("ROLE-C", parent="ROLE-P"))

    with pytest.raises(RoleInUseError) as blocked:
        with _Tx(connection).transaction():
            api.delete(
                "tenant-live", "project-live", 1, "ROLE-P",
                expected_revision=1, auth_context=auth(),
            )
    assert blocked.value.dependencies["child_roles"] == 1
    assert api.get("tenant-live", "project-live", 1, "ROLE-P", auth_context=auth()) is not None


def test_live_role_delete_is_scope_and_revision_bound(live):
    connection, api = live
    _create(connection, api, _role())
    _create(connection, api, _role(project="project-other"))
    _create(connection, api, _role(tenant="tenant-other"))

    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        with _Tx(connection).transaction():
            api.delete(
                "tenant-live", "project-live", 1, "ROLE-1",
                expected_revision=9, auth_context=auth(),
            )
    with pytest.raises(ValueError, match="ROLE_NOT_FOUND"):
        with _Tx(connection).transaction():
            api.delete(
                "tenant-live", "project-empty", 1, "ROLE-1",
                expected_revision=1, auth_context=auth(project="project-empty"),
            )

    with _Tx(connection).transaction():
        api.delete(
            "tenant-live", "project-live", 1, "ROLE-1",
            expected_revision=1, auth_context=auth(),
        )

    assert api.get("tenant-live", "project-live", 1, "ROLE-1", auth_context=auth()) is None
    assert api.get(
        "tenant-live", "project-other", 1, "ROLE-1",
        auth_context=auth(project="project-other"),
    ) is not None
    assert api.get(
        "tenant-other", "project-live", 1, "ROLE-1",
        auth_context=auth(tenant="tenant-other"),
    ) is not None