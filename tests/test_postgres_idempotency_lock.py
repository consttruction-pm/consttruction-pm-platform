from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore


class RecordingConnection:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))


def test_postgres_idempotency_lock_uses_transaction_scoped_advisory_lock():
    connection = RecordingConnection()
    store = PostgresSyncStateStore(connection)

    store.lock_idempotency("tenant", "project", "mutation-key")

    assert len(connection.calls) == 1
    sql, params = connection.calls[0]
    assert "pg_advisory_xact_lock" in sql
    assert "hashtextextended" in sql
    assert params == ("6:tenant|7:project|12:mutation-key",)


def test_postgres_idempotency_lock_key_includes_tenant_project_and_key():
    connection = RecordingConnection()
    store = PostgresSyncStateStore(connection)

    store.lock_idempotency("tenant-a", "project-a", "key-a")
    store.lock_idempotency("tenant-b", "project-a", "key-a")

    assert connection.calls[0][1] != connection.calls[1][1]


def test_postgres_idempotency_lock_identity_does_not_alias_delimiter_containing_components():
    connection = RecordingConnection()
    store = PostgresSyncStateStore(connection)

    store.lock_idempotency("a|b", "c", "d")
    store.lock_idempotency("a", "b|c", "d")

    assert connection.calls[0][1] != connection.calls[1][1]
