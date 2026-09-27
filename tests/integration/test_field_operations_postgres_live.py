from datetime import datetime, timezone
import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.field_operations import (
    FieldOperation,
    FieldOperationIdempotencyReuse,
    FieldOperationRevisionConflict,
    FieldOperationType,
    PostgresFieldOperationStore,
)


def make_operation(suffix: str, *, tenant_id: str = "live-tenant") -> FieldOperation:
    return FieldOperation(
        tenant_id=tenant_id,
        project_id=f"live-project-{suffix}",
        operation_id=f"operation-{suffix}",
        revision=0,
        operation_type=FieldOperationType.DAILY_LOG,
        occurred_at=datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc).isoformat(),
        actor_id="requester-1",
        location_ref="site-zone-a",
        payload={"note": "live field update", "items": ["crew", "equipment"]},
    )


def test_field_operations_live_round_trip_replay_and_conflict() -> None:
    suffix = uuid.uuid4().hex
    operation = make_operation(suffix)
    key = f"idempotency-{suffix}"

    with psycopg.connect(DSN) as connection:
        store = PostgresFieldOperationStore(connection)
        store.initialize()
        store.ensure_project(operation.tenant_id, operation.project_id)
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            created = store.persist(
                operation,
                expected_project_revision=0,
                idempotency_key=key,
            )

        assert created.project_revision == 1
        assert store.get(operation.tenant_id, operation.project_id, operation.operation_id) == created

        with PostgresTransactionManager(connection).transaction():
            replay = store.persist(
                operation,
                expected_project_revision=0,
                idempotency_key=key,
            )
        assert replay == created

        with PostgresTransactionManager(connection).transaction():
            with pytest.raises(FieldOperationRevisionConflict):
                store.persist(
                    FieldOperation(
                        **{**operation.__dict__, "operation_id": f"other-{suffix}"}
                    ),
                    expected_project_revision=0,
                    idempotency_key=f"stale-{suffix}",
                )

        with PostgresTransactionManager(connection).transaction():
            with pytest.raises(FieldOperationIdempotencyReuse):
                store.persist(
                    FieldOperation(
                        **{**operation.__dict__, "payload": {"note": "different"}}
                    ),
                    expected_project_revision=1,
                    idempotency_key=key,
                )

        connection.rollback()


def test_field_operations_live_transaction_rolls_back_mutation() -> None:
    suffix = uuid.uuid4().hex
    operation = make_operation(suffix)

    with psycopg.connect(DSN) as connection:
        store = PostgresFieldOperationStore(connection)
        store.initialize()
        store.ensure_project(operation.tenant_id, operation.project_id)
        connection.commit()

        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                persisted = store.persist(
                    operation,
                    expected_project_revision=0,
                    idempotency_key=f"rollback-{suffix}",
                )
                assert persisted.project_revision == 1
                raise RuntimeError("FORCED_ROLLBACK")

        assert store.get(operation.tenant_id, operation.project_id, operation.operation_id) is None
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT revision FROM project_field_operation_revisions "
                "WHERE tenant_id = %s AND project_id = %s",
                (operation.tenant_id, operation.project_id),
            )
            assert cursor.fetchone()[0] == 0
