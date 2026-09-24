from construction_pm.client_sync.conflict import ConflictContext, ConflictPresentation


def test_conflict_presentation_preserves_server_semantics() -> None:
    context = ConflictContext(
        error_code="STALE_REVISION",
        expected_revision=7,
        actual_revision=9,
        available_actions=("discard", "refresh_and_retry", "defer"),
        details={"resource": "activity", "id": "A1"},
    )
    view = ConflictPresentation.from_context(context)
    assert view.error_code == "STALE_REVISION"
    assert view.message_key == "sync.error.STALE_REVISION"
    assert view.available_actions == ("discard", "refresh_and_retry", "defer")


def test_conflict_requires_actions() -> None:
    try:
        ConflictContext("STALE_REVISION", 7, 9, (), {})
    except ValueError as exc:
        assert str(exc) == "AVAILABLE_ACTIONS_REQUIRED"
    else:
        raise AssertionError("conflict actions must be explicit")
