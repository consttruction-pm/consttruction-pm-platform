import json
from pathlib import Path


def test_authorization_contract_is_versioned_and_restrictive() -> None:
    path = Path(__file__).parents[2] / "shared" / "contracts" / "authorization.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "constructionpm://contracts/authorization/v1"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "contract_version", "tenant_id", "project_id", "user_id", "roles", "permission"
    }
    assert schema["properties"]["contract_version"]["const"] == "authorization.v1"
