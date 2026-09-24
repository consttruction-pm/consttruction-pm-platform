import sqlite3

import pytest

from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.queue import InMemoryOfflineMutationQueue, SQLiteOfflineMutationQueue

CTX = OfflineProjectContext("t-1","c-1","p-1",1,"cal-1",2,1,1)


def make_mutation(attempt: int = 0):
    return OfflineMutation(CTX, "register_resource", "k-1", {"resource_id":"R-1"}, 2, attempt)


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
    with pytest.raises(ValueError, match="already exists"):
        q.enqueue(m)


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


def test_in_memory_increment_attempt_preserves_identity():
    q = InMemoryOfflineMutationQueue()
    mutation = make_mutation()
    q.enqueue(mutation)
    updated = q.increment_attempt(mutation)
    assert updated.attempt == 1
    assert updated.fingerprint_payload() == mutation.fingerprint_payload()
    assert q.peek() == [updated]


def test_sqlite_increment_attempt_round_trip_preserves_identity():
    q = SQLiteOfflineMutationQueue(sqlite3.connect(":memory:"))
    mutation = make_mutation()
    q.enqueue(mutation)
    updated = q.increment_attempt(mutation)
    assert updated.attempt == 1
    assert updated.fingerprint_payload() == mutation.fingerprint_payload()
    assert q.peek() == [updated]


def test_increment_attempt_requires_queued_mutation():
    mutation = make_mutation()
    with pytest.raises(KeyError, match="not queued"):
        InMemoryOfflineMutationQueue().increment_attempt(mutation)
    with pytest.raises(KeyError, match="not queued"):
        SQLiteOfflineMutationQueue(sqlite3.connect(":memory:")).increment_attempt(mutation)


def test_sqlite_increment_attempt_participates_in_existing_transaction():
    connection = sqlite3.connect(":memory:")
    q = SQLiteOfflineMutationQueue(connection)
    mutation = make_mutation()
    q.enqueue(mutation)
    connection.execute("BEGIN")
    updated = q.increment_attempt(mutation)
    assert updated.attempt == 1
    connection.rollback()
    assert q.peek() == [mutation]
