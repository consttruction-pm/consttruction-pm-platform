import sqlite3

from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.queue import InMemoryOfflineMutationQueue, SQLiteOfflineMutationQueue

CTX = OfflineProjectContext("t-1","c-1","p-1",1,"cal-1",2,1,1)

def make_mutation():
    return OfflineMutation(CTX, "register_resource", "k-1", {"resource_id":"R-1"}, 2)

def test_in_memory_queue_is_idempotent_for_same_mutation():
    q=InMemoryOfflineMutationQueue(); m=make_mutation()
    q.enqueue(m); q.enqueue(m)
    assert q.peek() == [m]

def test_sqlite_queue_round_trips_typed_envelope():
    q=SQLiteOfflineMutationQueue(sqlite3.connect(":memory:")); m=make_mutation()
    q.enqueue(m)
    assert q.peek() == [m]
    q.remove(m)
    assert q.peek() == []

def test_sqlite_queue_rejects_duplicate_key():
    q=SQLiteOfflineMutationQueue(sqlite3.connect(":memory:")); m=make_mutation()
    q.enqueue(m)
    try:
        q.enqueue(m)
        assert False
    except ValueError as exc:
        assert "already exists" in str(exc)


def test_remove_is_context_scoped():
    other = OfflineProjectContext("t-2", "c-2", "p-2", 1, "cal-2", 1, 1, 1)
    first = OfflineMutation(CTX, "register_resource", "same-key", {"resource_id": "R-1"})
    second = OfflineMutation(other, "register_resource", "same-key", {"resource_id": "R-2"})
    q = InMemoryOfflineMutationQueue()
    q.enqueue(first)
    q.enqueue(second)
    q.remove(first)
    assert q.peek(limit=2) == [second]


def test_sqlite_remove_is_context_scoped():
    other = OfflineProjectContext("t-2", "c-2", "p-2", 1, "cal-2", 1, 1, 1)
    first = OfflineMutation(CTX, "register_resource", "same-key", {"resource_id": "R-1"})
    second = OfflineMutation(other, "register_resource", "same-key", {"resource_id": "R-2"})
    q = SQLiteOfflineMutationQueue(sqlite3.connect(":memory:"))
    q.enqueue(first)
    q.enqueue(second)
    q.remove(first)
    assert q.peek(limit=2) == [second]


def test_sqlite_queue_participates_in_existing_transaction():
    connection = sqlite3.connect(":memory:")
    q = SQLiteOfflineMutationQueue(connection)
    mutation = make_mutation()
    connection.execute("BEGIN")
    q.enqueue(mutation)
    connection.rollback()
    assert q.peek() == []
