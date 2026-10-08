from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).parents[2] / "src" / "construction_pm"
LEGACY = "construction_pm.resources.idempotency"


def test_resource_production_code_does_not_import_legacy_idempotency_module() -> None:
    violations: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        if path == SRC_ROOT / "resources" / "idempotency.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == LEGACY:
                violations.append(str(path))
    assert not violations, f"Legacy Resource idempotency imports found: {sorted(set(violations))}"
