from construction_pm.client_sync.persistence_contract import SyncStatePersistence
from construction_pm.client_sync.sqlite_sync_state import SQLiteSyncStateStore

def test_sqlite_adapter_exposes_shared_persistence_contract():
    for name in ("get_idempotency","put_idempotency","save_conflict","get_conflict"):
        assert hasattr(SQLiteSyncStateStore, name)

def test_contract_is_framework_neutral():
    assert SyncStatePersistence.__annotations__ == {}
