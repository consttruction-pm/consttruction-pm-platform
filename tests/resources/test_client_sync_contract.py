import json
from pathlib import Path

SCHEMA = Path("docs/contracts/client_sync_mutation_v1.schema.json")


def test_client_sync_contract_declares_context_idempotency_and_revision():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "client-sync.v1"
    assert schema["required"] == [
        "contract_version",
        "operation",
        "context",
        "idempotency_key",
        "mutation",
    ]
    assert schema["properties"]["context"]["required"] == [
        "tenant_id",
        "company_id",
        "project_id",
    ]
    assert schema["properties"]["expected_revision"]["type"] == ["integer", "null"]


def test_client_sync_contract_context_is_strict():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["context"]["additionalProperties"] is False
    assert schema["additionalProperties"] is False
