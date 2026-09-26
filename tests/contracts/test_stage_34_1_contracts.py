import json
from pathlib import Path


CONTRACTS = {
    "dependency-graph.v1.schema.json": "dependency-graph.v1",
    "control-intelligence-result.v1.schema.json": "control-intelligence-result.v1",
    "control-scenario.v1.schema.json": "control-scenario.v1",
    "control-impact.v1.schema.json": "control-impact.v1",
    "schedule-query.v1.schema.json": "schedule-query.v1",
    "schedule-query-result.v1.schema.json": "schedule-query-result.v1",
    "predictive-schedule-risk.v1.schema.json": "predictive-schedule-risk.v1",
    "change-claim-impact.v1.schema.json": "change-claim-impact.v1",
}


def test_stage_34_1_contracts_are_valid_versioned_json_schemas() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"

    for filename, version in CONTRACTS.items():
        path = root / filename
        payload = json.loads(path.read_text(encoding="utf-8"))

        assert payload["$schema"].endswith("/draft/2020-12/schema")
        assert payload["additionalProperties"] is False
        assert payload["properties"]["contract_version"]["const"] == version
        assert "$id" in payload


def test_stage_34_1_project_scoped_contracts_cap_revision_at_client_safe_integer() -> None:
    root = Path(__file__).parents[2] / "shared" / "contracts"
    expected_max = 9007199254740991

    for filename in CONTRACTS:
        payload = json.loads((root / filename).read_text(encoding="utf-8"))
        text = json.dumps(payload)
        assert str(expected_max) in text
