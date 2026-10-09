import os
import uuid
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.relationship_master_repository import (
    RelationshipMaster, RelationshipPersistenceError, PostgresRelationshipMasterRepository,
)
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.scheduling.time_duration import DurationUnit


def scope(revision=7):
    suffix = uuid.uuid4().hex
    return BackendScope(f"rel-tenant-{suffix}", f"rel-project-{suffix}", revision)


def relationship(current_scope):
    return RelationshipMaster(
        scope=current_scope, relationship_id="R-1", predecessor_id="A-1", successor_id="A-2",
        relationship_type=RelationshipType.SF, lag_value=Decimal("-1.25"),
        lag_unit=DurationUnit.WORKING_HOUR,
    )


def test_postgres_relationship_delete_is_revision_checked_and_scope_bound():
    current_scope = scope()
    with psycopg.connect(DSN) as connection:
        repository = PostgresRelationshipMasterRepository(connection)
        repository.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            stored = repository.save(relationship(current_scope))
        assert stored.record_revision == 1

        with pytest.raises(RelationshipPersistenceError, match="REVISION_CONFLICT"):
            with PostgresTransactionManager(connection).transaction():
                repository.delete(current_scope, "R-1", expected_revision=2)

        with pytest.raises(RelationshipPersistenceError, match="RELATIONSHIP_NOT_FOUND"):
            with PostgresTransactionManager(connection).transaction():
                repository.delete(BackendScope(current_scope.tenant_id + "-other", current_scope.project_id, 7), "R-1", expected_revision=1)

        with PostgresTransactionManager(connection).transaction():
            assert repository.delete(current_scope, "R-1", expected_revision=1) is True
        assert repository.get(current_scope, "R-1") is None

        with pytest.raises(RelationshipPersistenceError, match="RELATIONSHIP_NOT_FOUND"):
            with PostgresTransactionManager(connection).transaction():
                repository.delete(current_scope, "R-1", expected_revision=1)
