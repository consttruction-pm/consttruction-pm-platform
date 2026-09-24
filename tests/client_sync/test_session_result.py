from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.result import present_mutation_payload
from construction_pm.client_sync.session import ClientProjectSession


def session(revision=None):
    return ClientProjectSession(
        OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1),
        "api.v1",
        revision,
    )


def sync_payload(status="applied", revision=8):
    return {
        "contract_version": "client-sync-outcome.v1",
        "status": status,
        "operation": "update_activity",
        "revision": revision if status in {"applied", "replayed"} else None,
        "error_code": None if status in {"applied", "replayed"} else "STALE_REVISION",
        "retryable": False,
        "idempotency_key": "idem-1",
    }


def test_session_consumes_successful_mutation_result():
    result = present_mutation_payload(sync_payload())
    assert result is not None

    updated = session(7).apply_mutation_result(result)

    assert updated.revision == 8


def test_session_does_not_advance_on_conflict():
    result = present_mutation_payload(sync_payload("conflict"))
    assert result is not None

    current = session(7)
    assert current.apply_mutation_result(result) is current
    assert current.revision == 7


def test_session_does_not_advance_on_application_error():
    result = present_mutation_payload({
        "error": {
            "category": "conflict",
            "code": "STALE_REVISION",
            "message": "Revision conflict",
            "retryable": False,
        }
    })
    assert result is not None

    current = session(7)
    assert current.apply_mutation_result(result) is current
    assert current.revision == 7


def test_session_rejects_backward_result_revision():
    result = present_mutation_payload(sync_payload(revision=6))
    assert result is not None

    try:
        session(7).apply_mutation_result(result)
    except ValueError as exc:
        assert str(exc) == "authoritative revision cannot move backwards"
    else:
        raise AssertionError("expected ValueError")
