import pytest

from construction_pm.i18n.translation_coverage import (
    assert_translation_complete,
    validate_translation_coverage,
)


def test_translation_coverage_reports_missing_and_orphan_keys() -> None:
    coverage = validate_translation_coverage(
        {"nav.dashboard": "Dashboard", "nav.schedule": "Schedule"},
        {"nav.dashboard": "Tableau", "legacy.old": "Ancien"},
        language="fr",
    )

    assert coverage.required_keys == 2
    assert coverage.translated_keys == 2
    assert coverage.missing_keys == ("nav.schedule",)
    assert coverage.orphan_keys == ("legacy.old",)
    assert coverage.complete is False


def test_complete_translation_is_accepted() -> None:
    coverage = assert_translation_complete(
        {"nav.dashboard": "Dashboard", "nav.schedule": "Schedule"},
        {"nav.dashboard": "Tableau", "nav.schedule": "Calendrier"},
        language="fr",
    )
    assert coverage.complete is True


def test_invalid_empty_translation_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid translation"):
        validate_translation_coverage(
            {"nav.dashboard": "Dashboard"},
            {"nav.dashboard": "   "},
            language="fr",
        )
