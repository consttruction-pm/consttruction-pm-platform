import json
from pathlib import Path

def test_project_portability_contract_contains_reproducibility_context():
    root = Path(__file__).parents[2]
    contract = json.loads((root / "shared/contracts/project-portability.schema.json").read_text())
    assert {"schema_version","project","calculation_context"} <= set(contract["required"])
    assert {"calendar_id","calendar_version","scheduling_settings","calculation_schema_version"} <= set(contract["properties"]["calculation_context"]["required"])
