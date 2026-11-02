import sqlite3

import pytest

from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.offline_store_sqlite import SQLiteOfflineMutationStore


def make_mutation(
    *,
    mutation_id: str = "mutation-1",
    idempotency_key: str = "key-1",
    payload: dict[str, object] | None = None,
) -> OfflineMutation:
    return OfflineMutation(
        mutation_id=mutation_id,
        tenant_id="tenant-1",
        project_id="project-1",
        expected_revision=7,
        operation="activity.update",
        payload={"activity_id": "A-1", "name": "Updated"} if payload is None else payload,
        idempotency_key=idempotency_key,
    )


def test_sqlite_offline_store_persists_fifo_payload_across_restart_and_ack(tmp_path):
    database = tmp_path / "offline.sqlite3"
    first_connection = sqlite3.connect(database)
    first_store = SQLiteOfflineMutationStore(first_connection)
    first = make_mutation()
    second = make_mutation(
        mutation_id="mutation-2",
        idempotency_key="key-2",
        payload={"activity_id": "A-2", "tags": ["civil", "critical"]},
    )

    first_store.append(first)
    first_store.append(second)
    assert first_store.pending() == (first, second)
    first_connection.close()

    reopened_connection = sqlite3.connect(database)
    reopened_store = SQLiteOfflineMutationStore(reopened_connection)
    assert reopened_store.pending() == (first, second)
    reopened_store.acknowledge("mutation-1")
    assert reopened_store.pending() == (second,)
    reopened_connection.close()


def test_sqlite_offline_store_preserves_caller_owned_transaction_on_initialize():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE host_state (value TEXT NOT NULL)")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("INSERT INTO host_state(value) VALUES ('uncommitted')")

    SQLiteOfflineMutationStore(connection)

    assert connection.in_transaction
    connection.rollback()
    assert connection.execute("SELECT value FROM host_state").fetchall() == []
    connection.close()


def test_sqlite_offline_store_append_joins_caller_transaction_and_rolls_back():
    connection = sqlite3.connect(":memory:")
    store = SQLiteOfflineMutationStore(connection)
    mutation = make_mutation()

    connection.execute("BEGIN IMMEDIATE")
    store.append(mutation)
    assert connection.in_transaction
    assert store.pending() == (mutation,)
    connection.rollback()

    assert store.pending() == ()
    connection.close()


@pytest.mark.parametrize(
    ("duplicate", "message"),
    [
        (make_mutation(mutation_id="mutation-1"), "DUPLICATE_MUTATION_ID"),
        (
            make_mutation(mutation_id="mutation-2", idempotency_key="key-1"),
            "DUPLICATE_IDEMPOTENCY_KEY",
        ),
    ],
)
def test_sqlite_offline_store_rejects_duplicate_identity_or_idempotency(duplicate, message):
    connection = sqlite3.connect(":memory:")
    store = SQLiteOfflineMutationStore(connection)
    store.append(make_mutation())

    with pytest.raises(ValueError, match=message):
        store.append(duplicate)
    assert len(store.pending()) == 1
    connection.close()
