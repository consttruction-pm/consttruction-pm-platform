from pathlib import Path

FORBIDDEN_AUTHORITATIVE_IMPORTS = (
    "construction_pm.scheduling",
    "construction_pm.resources.calculator",
)

def test_backend_control_intelligence_boundary_does_not_import_authoritative_calculators() -> None:
    root = Path(__file__).parents[2]
    files = (
        root / "src/construction_pm/backend_p0/schedule_query.py",
        root / "src/construction_pm/control_intelligence/query.py",
        root / "src/construction_pm/control_intelligence/scenario.py",
        root / "src/construction_pm/control_intelligence/risk_engine.py",
    )
    for path in files:
        source = path.read_text()
        for forbidden in FORBIDDEN_AUTHORITATIVE_IMPORTS:
            assert f"import {forbidden}" not in source
            assert f"from {forbidden} " not in source

def test_web_control_intelligence_is_projection_only() -> None:
    root = Path(__file__).parents[2]
    source = (root / "apps/web/src/workspace-control-intelligence.ts").read_text()
    forbidden_markers = (
        "forwardPass(", "backwardPass(", "calculateDuration(",
        "earnedValue(", "criticalPath(", "resourceCost(",
    )
    for marker in forbidden_markers:
        assert marker not in source
