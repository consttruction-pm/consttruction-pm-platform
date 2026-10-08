from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).parents[2] / "src" / "construction_pm"


def test_resource_production_code_does_not_import_legacy_transaction_module() -> None:
    violations: list[str] = []

    for path in SRC_ROOT.rglob("*.py"):
        if path == SRC_ROOT / "resources" / "transactions.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "construction_pm.resources.transactions":
                violations.append(str(path))
            if path.is_relative_to(SRC_ROOT / "resources") and node.module == ".transactions":
                violations.append(str(path))

    assert not violations, (
        "Production code must use construction_pm.backend_p0.transactions; "
        f"legacy imports found: {sorted(set(violations))}"
    )
