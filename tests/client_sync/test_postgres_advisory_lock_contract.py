from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore


class RecordingConnection:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))


def test_postgres_idempotency_lock_uses_composite_mutation_identity():
    connection = RecordingConnection()
    store = PostgresSyncStateStore(connection)

    store.lock_idempotency("tenant-1", "project-7", "mutation-key-9")

    assert connection.calls == [
        (
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            ("10:tenant-1|9:project-7|14:mutation-key-9",),
        )
    ]
