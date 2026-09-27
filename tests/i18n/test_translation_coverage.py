import pytest
from construction_pm.i18n.translation_coverage import assert_translation_complete, validate_translation_coverage

def test_translation_coverage_reports_missing_and_orphan_keys():
    coverage=validate_translation_coverage({"nav.dashboard":"Dashboard","nav.schedule":"Schedule"},{"nav.dashboard":"Tableau","legacy.old":"Ancien"},language="fr")
    assert coverage.missing_keys == ("nav.schedule",); assert coverage.orphan_keys == ("legacy.old",); assert not coverage.complete

def test_complete_translation_is_accepted():
    assert assert_translation_complete({"nav.dashboard":"Dashboard"},{"nav.dashboard":"Tableau"},language="fr").complete

def test_invalid_empty_translation_is_rejected():
    with pytest.raises(ValueError, match="invalid translation"):
        validate_translation_coverage({"nav.dashboard":"Dashboard"},{"nav.dashboard":"   "},language="fr")
