from shared.client.client_context import ProjectContext
from shared.client.client_errors import ClientError
from shared.client.client_parity import ClientCapabilities, ClientKind


def test_project_context_is_shared_and_revision_aware() -> None:
    context = ProjectContext("tenant-1", "project-1", 7)
    assert context.revision == 7


def test_client_kinds_are_first_class() -> None:
    assert {k.value for k in ClientKind} == {"web", "desktop", "mobile"}


def test_shared_calculation_authority_is_explicit() -> None:
    capabilities = ClientCapabilities(offline=True)
    assert capabilities.scheduling == "shared-core"
    assert capabilities.progress_evm == "shared-core"
    assert capabilities.resource_cost == "shared-core"


def test_stable_client_error_preserves_actions() -> None:
    error = ClientError("STALE_REVISION", False, "error.stale_revision", ("discard", "refresh_and_retry"))
    assert error.code == "STALE_REVISION"
    assert error.available_actions == ("discard", "refresh_and_retry")
