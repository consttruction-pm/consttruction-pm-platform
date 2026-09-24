from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore

class FakeCursor:
    def __init__(self, rows=None): self.rows = list(rows or [])
    def fetchone(self): return self.rows.pop(0) if self.rows else None

class FakeConnection:
    def __init__(self): self.sql=[]; self.cursor=FakeCursor()
    def execute(self, sql, params=()):
        self.sql.append((sql, params))
        return self.cursor

def test_postgres_schema_has_database_unique_keys():
    c=FakeConnection()
    PostgresSyncStateStore(c).initialize()
    assert "PRIMARY KEY (tenant_id, project_id, idempotency_key)" in c.sql[0][0]
    assert "PRIMARY KEY (tenant_id, project_id, mutation_id)" in c.sql[1][0]

def test_postgres_adapter_uses_parameterized_sql():
    c=FakeConnection()
    store=PostgresSyncStateStore(c)
    store.get_idempotency("t1","p1","k1")
    assert "%s" in c.sql[0][0]
