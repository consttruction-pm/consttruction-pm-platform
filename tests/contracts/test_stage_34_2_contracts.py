import json
from pathlib import Path

CONTRACTS = {
    "field-daily-log.v1.schema.json": "field-daily-log.v1",
    "field-issue.v1.schema.json": "field-issue.v1",
    "change-notice.v1.schema.json": "change-notice.v1",
    "procurement-rfq.v1.schema.json": "procurement-rfq.v1",
}


def test_stage_34_2_p0_schemas_are_versioned_closed_json_schemas() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    for filename, version in CONTRACTS.items():
        payload = json.loads((root / filename).read_text(encoding="utf-8"))
        assert payload["$schema"].endswith("/draft/2020-12/schema")
        assert payload["additionalProperties"] is False
        assert payload["properties"]["contract_version"]["const"] == version


def test_stage_34_2_p0_schemas_include_project_revision_and_audit_contracts() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    for filename in CONTRACTS:
        payload = json.loads((root / filename).read_text(encoding="utf-8"))
        text = json.dumps(payload)
        assert "project_revision" in text
        assert "created_by" in text
        assert "updated_at" in text
