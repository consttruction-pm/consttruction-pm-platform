import os
import uuid
from datetime import datetime, timezone

import pytest

from construction_pm.p6_associated_resource_repository import (
    P6AssociatedResource,
    P6AssociatedResourceError,
    PostgresP6AssociatedResourceRepository,
)
from construction_pm.p6_resource_master_repository import P6Resource, PostgresP6ResourceRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def test_postgres_associated_resource_one_to_one_and_revision():
    suffix = uuid.uuid4().hex
    tenant = f"tenant-associated-{suffix}"
    project = f"project-associated-{suffix}"
    now = datetime.now(timezone.utc)
    with connect() as conn:
        resources = PostgresP6ResourceRepository(conn)
        resources.initialize()
        resources.save(P6Resource(tenant, project, 1, "R-1", "Crew"))
        resources.save(P6Resource(tenant, project, 1, "R-2", "Plant"))
        resources.save(P6Resource(tenant, f"{project}-other", 1, "R-1", "Crew Updated"))
        assert resources.get(tenant, project, 1, "R-1").name == "Crew Updated"
        associations = PostgresP6AssociatedResourceRepository(
            conn, user_exists=lambda _tenant, _user: True
        )
        associations.initialize()
        first = P6AssociatedResource(tenant, "user-1", "R-1", 1, "admin", now)
        assert associations.assign(first) == first
        with pytest.raises(P6AssociatedResourceError, match="ASSOCIATED_RESOURCE_REVISION_CONFLICT"):
            associations.assign(
                P6AssociatedResource(tenant, "user-1", "R-2", 2, "admin", now)
            )
        updated = P6AssociatedResource(tenant, "user-1", "R-2", 2, "admin", now)
        assert associations.assign(updated, expected_revision=1) == updated
        assert associations.get_for_resource(tenant, "R-2") == updated
        with pytest.raises(P6AssociatedResourceError, match="RESOURCE_ALREADY_ASSOCIATED"):
            associations.assign(P6AssociatedResource(tenant, "user-2", "R-2", 1, "admin", now))
        conn.rollback()
