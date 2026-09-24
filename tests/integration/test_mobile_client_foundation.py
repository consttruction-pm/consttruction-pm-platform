from pathlib import Path


def test_mobile_runtime_foundation_exists() -> None:
    root = Path("apps/mobile/src")
    assert (root / "runtime.ts").exists()
    assert (root / "index.ts").exists()


def test_mobile_is_first_class_surface() -> None:
    package = Path("apps/mobile/package.json").read_text()
    assert '"@construction-pm/mobile"' in package
