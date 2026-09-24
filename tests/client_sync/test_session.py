from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.session import ClientProjectSession


def test_project_session_validates_and_carries_revision():
    context = OfflineProjectContext("t", "c", "p", 1, "cal", 1, 1, 1)
    session = ClientProjectSession(context=context, api_contract_version="api.v1", revision=7)

    assert session.mutation_context() == context
    assert session.with_revision(8).revision == 8
    assert session.with_revision(8).context == context


def test_project_session_rejects_invalid_revision():
    context = OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1)

    try:
        ClientProjectSession(context=context, api_contract_version="api.v1", revision=-1).validate()
    except ValueError as exc:
        assert str(exc) == "revision must be non-negative when provided"
    else:
        raise AssertionError("expected ValueError")


def test_project_session_requires_api_contract_version():
    context = OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1)
    session = ClientProjectSession(context=context, api_contract_version=" ")

    try:
        session.validate()
    except ValueError as exc:
        assert str(exc) == "api_contract_version is required"
    else:
        raise AssertionError("expected ValueError")
