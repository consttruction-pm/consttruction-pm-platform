from pathlib import Path

from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.offline_store_json import JsonFileOfflineMutationStore


def mutation() -> OfflineMutation:
    return OfflineMutation(
        mutation_id="m1",
        tenant_id="t1",
        project_id="p1",
        expected_revision=4,
        operation="update_activity",
        payload={"activity_id": "A1", "duration": "4"},
        idempotency_key="idem-1",
    )


def test_json_store_survives_new_instance(tmp_path: Path) -> None:
    path = tmp_path / "offline.json"
    JsonFileOfflineMutationStore(path).append(mutation())

    reopened = JsonFileOfflineMutationStore(path)
    assert reopened.pending()[0].mutation_id == "m1"
    assert reopened.pending()[0].payload["activity_id"] == "A1"


def test_acknowledge_persists(tmp_path: Path) -> None:
    path = tmp_path / "offline.json"
    store = JsonFileOfflineMutationStore(path)
    store.append(mutation())
    store.acknowledge("m1")

    assert JsonFileOfflineMutationStore(path).pending() == ()
