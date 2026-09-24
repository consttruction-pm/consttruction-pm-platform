from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.outcome import SyncMutationOutcome
from construction_pm.client_sync.session import ClientProjectSession


def session(revision=None):
    return ClientProjectSession(
        OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1),
        "api.v1",
        revision,
    )


def test_applied_outcome_advances_revision():
    updated = session(7).apply_authoritative_outcome(
        SyncMutationOutcome(status="applied", revision=8)
    )
    assert updated.revision == 8


def test_replayed_outcome_advances_revision():
    updated = session(7).apply_authoritative_outcome(
        SyncMutationOutcome(status="replayed", revision=9)
    )
    assert updated.revision == 9


def test_conflict_does_not_advance_revision():
    current = session(7)
    assert current.apply_authoritative_outcome(
        SyncMutationOutcome(status="conflict", error_code="STALE_REVISION")
    ) is current


def test_rejected_does_not_advance_revision():
    current = session(7)
    assert current.apply_authoritative_outcome(
        SyncMutationOutcome(status="rejected", error_code="VALIDATION_ERROR")
    ) is current


def test_successful_outcome_requires_revision():
    try:
        session(7).apply_authoritative_outcome(
            SyncMutationOutcome(status="applied")
        )
    except ValueError as exc:
        assert str(exc) == "successful outcome requires revision"
    else:
        raise AssertionError("expected ValueError")


def test_authoritative_revision_cannot_move_backwards():
    try:
        session(8).apply_authoritative_outcome(
            SyncMutationOutcome(status="replayed", revision=7)
        )
    except ValueError as exc:
        assert str(exc) == "authoritative revision cannot move backwards"
    else:
        raise AssertionError("expected ValueError")
