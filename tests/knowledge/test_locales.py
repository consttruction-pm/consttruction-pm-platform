from __future__ import annotations

import pytest

from construction_pm.knowledge.locales import (
    DEFAULT_LOCALE,
    FALLBACK_LOCALE,
    LEGACY_LOCALES,
    LOCALES,
    PRODUCT_LOCALES,
    RTL_LOCALES,
    SOURCE_LANGUAGE,
    SUPPORTED_LANGUAGE_CODES,
    SUPPORTED_LOCALES,
    TARGET_LOCALES,
    canonical_locale,
    detect_locale,
    direction,
    is_product_locale,
    is_rtl,
    language_code,
    locale_definition,
    locale_registry,
    localized_join,
    require_locale,
    resolve_response_locale,
    supported_locale,
    text_direction,
    translation_locale_candidates,
)
from construction_pm.knowledge.model import KnowledgeError

EXPECTED_LOCALES = ("fa", "en", "de", "zh-Hans", "ar", "fr", "ja", "ko", "ru")
EXPECTED_PRODUCT = ("fa", "en", "de", "zh-Hans", "ar", "fr", "ja", "ko")
EXPECTED_TARGETS = ("fa", "de", "zh-Hans", "ar", "fr", "ja", "ko")

SCRIPT_SAMPLES = {
    "fa": "چگونه یک پروژه ایجاد کنم؟",
    "en": "How do I create a project?",
    "de": "Wie erstelle ich ein Projekt?",
    "zh-Hans": "如何创建项目？",
    "ar": "كيف يمكنني إنشاء مشروع؟",
    "fr": "Comment créer un projet ?",
    "ja": "プロジェクトを作成するには？",
    "ko": "프로젝트를 어떻게 생성합니까?",
    "ru": "Как создать проект?",
}


def test_eight_product_locales_and_seven_targets() -> None:
    assert SUPPORTED_LOCALES == EXPECTED_LOCALES
    assert PRODUCT_LOCALES == EXPECTED_PRODUCT
    assert TARGET_LOCALES == EXPECTED_TARGETS
    assert LEGACY_LOCALES == ("ru",)
    assert len(LOCALES) == 9
    assert len(PRODUCT_LOCALES) == 8
    assert len(TARGET_LOCALES) == 7
    assert SUPPORTED_LANGUAGE_CODES == ("fa", "en", "de", "zh", "ar", "fr", "ja", "ko", "ru")


def test_registry_exposes_source_default_and_fallback_language() -> None:
    for item in locale_registry():
        assert item["source_language"] == SOURCE_LANGUAGE
        assert item["default_language"] == DEFAULT_LOCALE
        assert item["fallback_language"] == FALLBACK_LOCALE
        assert item["locale"] == canonical_locale(item["locale"])
        assert item["product"] is (item["locale"] != "ru")
        assert item["legacy"] is (item["locale"] == "ru")


def test_chinese_is_one_product_locale() -> None:
    assert canonical_locale("zh") == "zh-Hans"
    assert canonical_locale("zh-Hans") == "zh-Hans"
    assert canonical_locale("zh-CN") == "zh-Hans"
    assert canonical_locale("zh-TW") == "zh-Hans"
    assert canonical_locale("zh-Hant") == "zh-Hans"
    assert canonical_locale("zh_hk") == "zh-Hans"
    assert locale_definition("zh-Hans").script == "Han-Simplified"
    assert language_code("zh-Hans") == "zh"
    assert translation_locale_candidates("zh-Hans") == ("zh-Hans", "zh-CN", "zh-TW")
    assert translation_locale_candidates("zh-Hant") == ("zh-Hans", "zh-CN", "zh-TW")


def test_russian_is_legacy_but_still_readable() -> None:
    assert canonical_locale("ru-RU") == "ru"
    assert canonical_locale("ru") == "ru"
    assert not is_product_locale("ru")
    assert is_product_locale("fa")
    assert "ru" not in PRODUCT_LOCALES
    assert "ru" not in TARGET_LOCALES


def test_locale_aliases_and_region_tags_resolve() -> None:
    assert canonical_locale("fa-IR") == "fa"
    assert canonical_locale("de-AT") == "de"
    assert canonical_locale("fr-CA") == "fr"
    assert canonical_locale("ru-RU") == "ru"
    assert canonical_locale("EN-us") == "en"
    assert canonical_locale("ar-SA") == "ar"
    assert supported_locale("ko-KR")


def test_unsupported_locale_is_rejected_when_required() -> None:
    assert canonical_locale("pt-BR", default=None) is None
    assert not supported_locale("pt-BR")
    with pytest.raises(KnowledgeError) as failure:
        require_locale("pt-BR")
    assert "KNOWLEDGE_LOCALE_UNSUPPORTED" in str(failure.value)


@pytest.mark.parametrize("locale,question", sorted(SCRIPT_SAMPLES.items()))
def test_script_detection_identifies_every_locale(locale: str, question: str) -> None:
    assert detect_locale(question) == locale


def test_traditional_and_simplified_chinese_detect_as_one_locale() -> None:
    assert detect_locale("建立專案") == "zh-Hans"
    assert detect_locale("建立项目") == "zh-Hans"
    # A zh-Hant request is served by the same Chinese translation target.
    assert resolve_response_locale(requested="zh-Hant") == "zh-Hans"
    assert resolve_response_locale(requested="zh-TW") == "zh-Hans"


def test_arabic_accusative_and_persian_are_distinguished() -> None:
    assert detect_locale("مشروعاً؟") == "ar"
    assert detect_locale("كيف أنشئ مشروعاً؟") == "ar"
    assert detect_locale("چگونه پروژه بسازم؟") == "fa"
    assert detect_locale("یک پروژه") == "fa"


def test_rtl_and_ltr_directions() -> None:
    assert set(RTL_LOCALES) == {"fa", "ar"}
    assert is_rtl("fa") and is_rtl("ar")
    assert not is_rtl("ru") and not is_rtl("zh-TW")
    assert direction("he") == "ltr"  # unknown locale falls back to LTR
    info = text_direction("ar")
    assert info["rtl"] is True
    assert info["direction"] == "rtl"


def test_response_locale_precedence() -> None:
    question = "Как создать проект?"
    # Explicit request wins over the question language.
    assert resolve_response_locale(requested="ru", question=question) == "ru"
    # Profile preference wins over detection.
    assert resolve_response_locale(question=question, profile_locale="de") == "de"
    # Detected question language is used when nothing is configured.
    assert resolve_response_locale(question=question) == "ru"
    # Product default otherwise.
    assert resolve_response_locale(question="") == DEFAULT_LOCALE
    with pytest.raises(KnowledgeError):
        resolve_response_locale(requested="pt-BR", question=question)


def test_localized_join_uses_language_separator() -> None:
    assert localized_join("fa", ("الف", "ب")) == "الف، ب"
    assert localized_join("ar", ("الف", "ب")) == "الف، ب"
    assert localized_join("en", ("a", "b")) == "a, b"
    assert localized_join("ru", ("а", "б")) == "а, б"
