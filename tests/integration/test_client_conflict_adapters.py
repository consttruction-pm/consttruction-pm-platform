from shared.client.conflict_presentation import build_conflict_view


def test_all_clients_preserve_conflict_semantics() -> None:
    expected = ("discard", "refresh_and_retry", "defer")
    views = [
        build_conflict_view(
            client,
            error_code="STALE_REVISION",
            available_actions=expected,
            expected_revision=7,
            actual_revision=9,
        )
        for client in ("web", "desktop", "mobile")
    ]

    assert {v.client for v in views} == {"web", "desktop", "mobile"}
    for view in views:
        assert view.error_code == "STALE_REVISION"
        assert view.available_actions == expected
        assert view.context["expected_revision"] == 7
        assert view.context["actual_revision"] == 9


def test_adapter_does_not_change_action_order_or_identity() -> None:
    actions = ("discard", "refresh_and_retry", "defer")
    for client in ("web", "desktop", "mobile"):
        view = build_conflict_view(
            client,
            error_code="STALE_REVISION",
            available_actions=actions,
            expected_revision=2,
            actual_revision=3,
        )
        assert view.available_actions == actions
