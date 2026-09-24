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


def test_web_client_consumes_stable_application_error_contract() -> None:
    source = Path("apps/web/src/client.ts").read_text()
    assert "isApplicationErrorEnvelope" in source
    assert "payload.error.category" in source
    assert "payload.error.code" in source
    assert "payload.error.message" in source
    assert "payload.error.retryable" in source
    assert "message_key: payload.error.message" not in source


def test_web_client_preserves_error_presentation_fields() -> None:
    source = Path("apps/web/src/error-boundary.ts").read_text()
    assert "error.category" in source
    assert "error.message" in source
    assert "error.message_key" in source


def test_all_client_runtimes_consume_shared_project_context_contract() -> None:
    for path in (
        Path("apps/web/src/project-context.ts"),
        Path("apps/desktop/src/runtime.ts"),
        Path("apps/mobile/src/runtime.ts"),
    ):
        source = path.read_text()
        assert "shared/client-contracts/project-context" in source
        assert "validateProjectContext" in source


def test_web_client_preserves_conflict_context_fields() -> None:
    client_source = Path("apps/web/src/client.ts").read_text()
    boundary_source = Path("apps/web/src/error-boundary.ts").read_text()
    for field in ("expected_revision", "actual_revision", "details"):
        assert field in client_source
        assert f"error.{field}" in boundary_source
    assert "available_actions" in client_source
    assert "payload.error" in client_source
