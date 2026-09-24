from pathlib import Path


def test_desktop_runtime_foundation_exists() -> None:
    root = Path("apps/desktop/src")
    assert (root / "runtime.ts").exists()
    assert (root / "index.ts").exists()


def test_desktop_is_marked_as_standalone_surface() -> None:
    package = Path("apps/desktop/package.json").read_text()
    assert '"@construction-pm/desktop"' in package
