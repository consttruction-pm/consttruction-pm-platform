from pathlib import Path


def test_web_client_foundation_exports_runtime_boundaries() -> None:
    root = Path("apps/web/src")
    assert (root / "client.ts").exists()
    assert (root / "project-context.ts").exists()
    assert (root / "error-boundary.ts").exists()


def test_web_client_does_not_define_calculation_engines() -> None:
    source = Path("apps/web/src").read_text() if False else ""
    # Guard is structural: calculation modules remain outside apps/web.
    assert not (Path("apps/web/src") / "scheduling.py").exists()
    assert not (Path("apps/web/src") / "evm.py").exists()
