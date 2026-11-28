"""Live PostgreSQL acceptance for P6 resource master delete.

Creates a throw-away schema, then drives the same ``P6ResourceAPI`` and
``PostgresP6ResourceRepository`` the production runtime composes. Proves:
- an unreferenced resource is deleted and its own rate/capacity/spread facts go
  with it (no orphan),
- a resource with an assignment is refused with per-reference counts and no row
  is written,
- tenant/project scope and the record-revision guard are enforced,
- a same-id resource in another project or tenant is untouched.
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
from construction_pm.calendar_master_repository import (  # noqa: E402
    PostgresCalendarMasterRepository,
)
from construction_pm.p6_resource_assignment_repository import (  # noqa: E402
    PostgresP6ResourceAssignmentPeriodRepository,
    PostgresP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_capacity_repository import (  # noqa: E402
    PostgresP6ResourceCapacityRepository,
)
from construction_pm.p6_resource_master_api import P6ResourceAPI  # noqa: E402
from construction_pm.p6_resource_master_repository import (  # noqa: E402
    P6Resource,
    PostgresP6ResourceRepository,
    ResourceInUseError,
)
from construction_pm.p6_resource_rate_repository import (  # noqa: E402
    PostgresP6ResourceRateRepository,
)
from construction_pm.p6_resource_spread_repository import (  # noqa: E402
    PostgresP6ResourceSpreadRepository,
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

    schema = f"cubi_res_{uuid.uuid4().hex[:12]}"
    connection = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={schema}",
    )
    connection.execute(f'CREATE SCHEMA "{schema}"')
    connection.autocommit = False
    return connection, schema


@pytest.fixture()
def live():
    connection, schema = _connect()
    try:
        PostgresP6ResourceRepository(connection).initialize()
        PostgresP6ResourceAssignmentRepository(connection).initialize()
        PostgresP6ResourceAssignmentPeriodRepository(connection).initialize()
        PostgresP6ResourceRateRepository(connection).initialize()
        PostgresP6ResourceCapacityRepository(connection).initialize()
        PostgresP6ResourceSpreadRepository(connection).initialize()
        calendars = PostgresCalendarMasterRepository(connection)
        calendars.initialize()
        connection.commit()
        yield connection, P6ResourceAPI(
            PostgresP6ResourceRepository(connection), default_project_policy(), calendars
        )
    finally:
        connection.rollback()
        connection.autocommit = True
        connection.execute("SET search_path TO public")
        connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
        connection.close()


def _resource(resource_id="R-1", *, tenant="tenant-live", project="project-live", revision=1, **overrides):
    return P6Resource(
        tenant_id=tenant,
        project_id=project,
        project_revision=revision,
        resource_id=resource_id,
        name="Civil Crew",
        **overrides,
    )


def _create(connection, api, resource):
    with _Tx(connection).transaction():
        created = api.create(resource, auth_context=auth(resource.tenant_id, resource.project_id))
    return created


def test_live_resource_delete_removes_owned_facts(live):
    connection, api = live
    _create(connection, api, _resource())
    connection.execute(
        "INSERT INTO p6_resource_rate_fact "
        "(tenant_id,project_id,project_revision,resource_id,identity,rate,basis,currency,unit,effective_from,effective_to,source) "
        "VALUES ('tenant-live','project-live',1,'R-1','i1','10','hour','USD','hour','2026-01-01',NULL,'manual'),"
        "('tenant-live','project-live',1,'R-1','i2','12','hour','USD','hour','2026-02-01',NULL,'manual')"
    )
    connection.execute(
        "INSERT INTO p6_resource_rate_supersession "
        "(tenant_id,project_id,resource_id,identity,superseded_by_identity,recorded_at) "
        "VALUES ('tenant-live','project-live','R-1','i1','i2','2026-02-01T00:00:00Z')"
    )
    connection.execute(
        "INSERT INTO p6_resource_capacity_segment "
        "(tenant_id,project_id,project_revision,resource_id,identity,max_units,unit_basis,hours_per_time_period,effective_from,effective_to,source) "
        "VALUES ('tenant-live','project-live',1,'R-1','c1','8','hour','8','2026-01-01',NULL,'manual')"
    )
    connection.execute(
        "INSERT INTO p6_resource_spread_bucket "
        "(tenant_id,project_id,project_revision,spread_id,resource_id,period_id,period_start,period_end,spread_type,metric,value,unit,currency) "
        "VALUES ('tenant-live','project-live',1,'S-1','R-1','P-1','2026-01-01','2026-01-31','resource','units','8','hour','USD')"
    )
    connection.commit()

    with _Tx(connection).transaction():
        result = api.delete(
            "tenant-live", "project-live", 1, "R-1",
            expected_revision=1, auth_context=auth(),
        )

    assert result["deleted"] is True
    assert result["removed_rows"]["rate_facts"] == 2
    assert result["removed_rows"]["capacity_segments"] == 1
    assert result["removed_rows"]["spread_buckets"] == 1
    assert api.get("tenant-live", "project-live", 1, "R-1", auth_context=auth()) is None
    for table in (
        "p6_resource_rate_fact",
        "p6_resource_rate_supersession",
        "p6_resource_capacity_segment",
        "p6_resource_spread_bucket",
    ):
        assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_live_resource_delete_refuses_an_assignment_and_commits_nothing(live):
    connection, api = live
    _create(connection, api, _resource())
    connection.execute(
        "INSERT INTO p6_resource_assignment "
        "(tenant_id,project_id,project_revision,assignment_id,activity_id,resource_id) "
        "VALUES ('tenant-live','project-live',1,'ASN-1','A-1','R-1')"
    )
    connection.commit()

    with pytest.raises(ResourceInUseError) as blocked:
        with _Tx(connection).transaction():
            api.delete(
                "tenant-live", "project-live", 1, "R-1",
                expected_revision=1, auth_context=auth(),
            )
    assert blocked.value.dependencies["assignments"] == 1
    stored = api.get("tenant-live", "project-live", 1, "R-1", auth_context=auth())
    assert stored is not None
    assert connection.execute(
        "SELECT COUNT(*) FROM p6_resource_assignment"
    ).fetchone()[0] == 1


def test_live_resource_delete_is_scope_and_revision_bound(live):
    connection, api = live
    _create(connection, api, _resource())
    _create(connection, api, _resource("R-1", project="project-other"))
    _create(connection, api, _resource("R-1", tenant="tenant-other"))

    with pytest.raises(ValueError, match="REVISION_CONFLICT"):
        with _Tx(connection).transaction():
            api.delete(
                "tenant-live", "project-live", 1, "R-1",
                expected_revision=9, auth_context=auth(),
            )

    with _Tx(connection).transaction():
        api.delete(
            "tenant-live", "project-live", 1, "R-1",
            expected_revision=1, auth_context=auth(),
        )

    assert api.get("tenant-live", "project-live", 1, "R-1", auth_context=auth()) is None
    assert api.get(
        "tenant-live", "project-other", 1, "R-1",
        auth_context=auth(project="project-other"),
    ) is not None
    assert api.get(
        "tenant-other", "project-live", 1, "R-1",
        auth_context=auth(tenant="tenant-other"),
    ) is not None