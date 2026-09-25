import json
from pathlib import Path


def test_sync_project_revision_contract_is_versioned():
    root = Path(__file__).resolve().parents[2]
    payload = json.loads((root / "shared" / "contracts" / "sync-project-revision.schema.json").read_text(encoding="utf-8"))

    assert payload["$id"] == "constructionpm://contracts/sync-project-revision/v1"
    assert payload["properties"]["contract_version"]["const"] == "sync-project-revision.v1"
    assert payload["required"] == ["contract_version", "tenant_id", "project_id", "revision"]
