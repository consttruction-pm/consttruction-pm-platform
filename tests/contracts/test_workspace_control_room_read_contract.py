from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_workspace_read_contract_includes_document_snapshots() -> None:
    contract = json.loads(
        (ROOT / "shared" / "contracts" / "workspace-control-room-read.v1.schema.json").read_text()
    )
    documents = contract["properties"]["documents"]
    item = documents["items"]

    assert documents["type"] == "array"
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {
        "document_id",
        "tenant_id",
        "project_id",
        "resource_type",
        "title",
        "status",
        "storage_ref",
        "content_hash",
        "linked_entity_refs",
        "revision",
    }
    assert item["properties"]["content_hash"]["pattern"] == "^sha256:[0-9a-fA-F]{64}$"
    assert item["properties"]["revision"]["maximum"] == 9_007_199_254_740_991
