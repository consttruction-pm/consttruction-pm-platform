"""CUBI knowledge and assistant locale registry.

The product ships ten locales and nine working languages behind one explicit
registry. Nothing in the knowledge, search, assistant or workflow layers may
hard-code a locale check; every subsystem resolves language through this module
so that adding a locale is a registry change, not a set of scattered branches.

The registry itself is CUBI-owned product metadata. It contains no third-party
provider name, model name or remote translation dependency.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping

from .model import KnowledgeError

DEFAULT_LOCALE = "en"
FALLBACK_LOCALE = "en"
SOURCE_LANGUAGE = "en"


@dataclass(frozen=True)
class LocaleDefinition:
    locale: str
    language_code: str
    display_name: str
    english_name: str
    direction: str
    script: str
    aliases: tuple[str, ...] = ()

    @property
    def is_rtl(self) -> bool:
        return self.direction == "rtl"

    def as_dict(self) -> dict[str, object]:
        return {
            "locale": self.locale,
            "language_code": self.language_code,
            "display_name": self.display_name,
            "english_name": self.english_name,
            "direction": self.direction,
            "script": self.script,
            "aliases": list(self.aliases),
            "source_language": SOURCE_LANGUAGE,
            "default_language": DEFAULT_LOCALE,
            "fallback_language": FALLBACK_LOCALE,
        }


_LOCALE_DEFINITIONS: tuple[LocaleDefinition, ...] = (
    LocaleDefinition("fa", "fa", "فارسی", "Persian", "rtl", "Arabic", ("fa-ir", "prs", "persian", "farsi")),
    LocaleDefinition("en", "en", "English", "English", "ltr", "Latin", ("en-us", "en-gb", "english")),
    LocaleDefinition("de", "de", "Deutsch", "German", "ltr", "Latin", ("de-de", "german")),
    LocaleDefinition("zh-CN", "zh", "简体中文", "Simplified Chinese", "ltr", "Han-Simplified", ("zh", "zh-hans", "zh-sg", "chinese-simplified")),
    LocaleDefinition("zh-TW", "zh", "繁體中文", "Traditional Chinese", "ltr", "Han-Traditional", ("zh-hant", "zh-hk", "zh-mo", "chinese-traditional")),
    LocaleDefinition("ar", "ar", "العربية", "Arabic", "rtl", "Arabic", ("ar-sa", "ar-ae", "arabic")),
    LocaleDefinition("fr", "fr", "Français", "French", "ltr", "Latin", ("fr-fr", "french")),
    LocaleDefinition("ja", "ja", "日本語", "Japanese", "ltr", "Japanese", ("ja-jp", "japanese")),
    LocaleDefinition("ko", "ko", "한국어", "Korean", "ltr", "Hangul", ("ko-kr", "korean")),
    LocaleDefinition("ru", "ru", "Русский", "Russian", "ltr", "Cyrillic", ("ru-ru", "russian")),
)

LOCALES: tuple[LocaleDefinition, ...] = _LOCALE_DEFINITIONS
SUPPORTED_LOCALES: tuple[str, ...] = tuple(item.locale for item in LOCALES)
SUPPORTED_LANGUAGE_CODES: tuple[str, ...] = tuple(
    dict.fromkeys(item.language_code for item in LOCALES)
)
RTL_LOCALES: tuple[str, ...] = tuple(item.locale for item in LOCALES if item.is_rtl)

_BY_LOCALE: dict[str, LocaleDefinition] = {item.locale: item for item in LOCALES}
_ALIASES: dict[str, str] = {}
for _item in LOCALES:
    _ALIASES[_item.locale.lower()] = _item.locale
    # Simplified and Traditional Chinese share the language code "zh". The
    # first definition (Simplified) owns the bare code; "zh" must not be
    # rebound to Traditional by a later registry entry.
    _ALIASES.setdefault(_item.language_code.lower(), _item.locale)
    for _alias in _item.aliases:
        _ALIASES.setdefault(_alias.lower(), _item.locale)


def supported_locale(value: object) -> bool:
    return isinstance(value, str) and canonical_locale(value, default=None) is not None


def canonical_locale(value: object, *, default: str | None = DEFAULT_LOCALE) -> str | None:
    """Resolve any supported tag or alias to one canonical locale.

    ``zh`` maps to Simplified Chinese and ``zh-Hant``/``zh-TW`` to Traditional
    Chinese, because the product ships them as separate locales. An unknown tag
    returns ``default`` (or ``None`` when no default is supplied); callers that
    accept client input must pass ``default=None`` and reject the value.
    """

    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    if not isinstance(value, str):
        return default
    tag = value.strip().replace("_", "-").lower()
    if tag in _ALIASES:
        return _ALIASES[tag]
    # Accept a base language plus a region, e.g. "pt-BR" is unsupported but
    # "de-AT" should still resolve to German.
    base = tag.split("-", 1)[0]
    if base in _ALIASES and base not in {"zh"}:
        return _ALIASES[base]
    return default


def require_locale(value: object, *, code: str = "KNOWLEDGE_LOCALE_UNSUPPORTED") -> str:
    resolved = canonical_locale(value, default=None)
    if resolved is None:
        raise KnowledgeError(code)
    return resolved


def locale_definition(locale: object, *, default: str | None = DEFAULT_LOCALE) -> LocaleDefinition | None:
    resolved = canonical_locale(locale, default=default)
    return None if resolved is None else _BY_LOCALE[resolved]


def direction(locale: object) -> str:
    definition = locale_definition(locale)
    return "ltr" if definition is None else definition.direction


def is_rtl(locale: object) -> bool:
    return direction(locale) == "rtl"


def language_code(locale: object) -> str:
    definition = locale_definition(locale)
    return FALLBACK_LOCALE if definition is None else definition.language_code


def locale_registry() -> tuple[dict[str, object], ...]:
    return tuple(item.as_dict() for item in LOCALES)


# -- deterministic script identification ---------------------------------
# The detector is intentionally rule-based: the assistant must not call an
# external language-identification service. Order matters because Japanese and
# Korean use Han characters in addition to their own scripts.

_HANGUL = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
_KANA = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_CYRILLIC = re.compile(r"[\u0400-\u04ff]")
_ARABIC_SCRIPT = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]")
_LATIN = re.compile(r"[A-Za-z\u00c0-\u024f]")

# Characters that only occur in one Chinese orthography. These are seed sets,
# not an exhaustive dictionary; shared characters fall back to Simplified.
_SIMPLIFIED_ONLY = set("这为说时过来还们么与东车门书见长国产业务开发运进问题会话负责")
_TRADITIONAL_ONLY = set("這為說時過來還們麼與東車門書見長國產業務開發運進問題會話負責專體應該網路設計階段標準備註冊機構")

_GERMAN_HINTS = {
    "der", "die", "das", "und", "nicht", "mit", "für", "auf", "ist", "den",
    "dem", "des", "ein", "eine", "einen", "zu", "von", "im", "sich", "werden",
    "projekt", "erstellen", "planen", "ressource", "kalender", "bericht",
}
_FRENCH_HINTS = {
    "le", "la", "les", "un", "une", "des", "et", "est", "pour", "avec", "sur",
    "dans", "du", "au", "aux", "ce", "cette", "projet", "créer", "planifier",
    "ressource", "calendrier", "rapport", "activité",
}
_ENGLISH_HINTS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "be", "by", "as", "at", "from", "that", "this", "it",
    "how", "what", "when", "where", "which", "do", "does", "can", "project",
    "create", "schedule", "activity", "resource", "calendar", "report",
}
_PERSIAN_ONLY = set("پچژگ")
_ARABIC_ONLY = set("ةى")
_AR_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_ARABIC_WORDS = {"و", "في", "من", "على", "إلى", "هذا", "هذه", "كيف", "هل", "ما", "لا", "عن"}
_PERSIAN_WORDS = {"و", "در", "از", "به", "این", "آن", "برای", "چگونه", "است", "که", "را", "یک"}


def _latin_words(value: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[A-Za-z\u00c0-\u024f]+", value)}


def _han_orthography(value: str) -> str:
    simplified = sum(1 for character in value if character in _SIMPLIFIED_ONLY)
    traditional = sum(1 for character in value if character in _TRADITIONAL_ONLY)
    if traditional > simplified:
        return "zh-TW"
    return "zh-CN"


def detect_locale(value: str, *, default: str = DEFAULT_LOCALE) -> str:
    """Identify the locale of a question or a stored text record.

    This is script-based and deterministic. Persian and Arabic share a script,
    so Persian-specific letters decide between them; Japanese and Korean are
    separated from Chinese by kana and Hangul; Cyrillic is Russian; Latin text
    is separated by high-frequency function words and diacritics.
    """

    if not isinstance(value, str) or not value.strip():
        return default
    text = unicodedata.normalize("NFKC", value)
    hangul = len(_HANGUL.findall(text))
    kana = len(_KANA.findall(text))
    han = len(_HAN.findall(text))
    cyrillic = len(_CYRILLIC.findall(text))
    arabic = len(_ARABIC_SCRIPT.findall(text))
    latin = len(_LATIN.findall(text))
    if hangul:
        return "ko"
    if kana:
        return "ja"
    if han and han >= max(latin, cyrillic, arabic):
        return _han_orthography(text)
    if cyrillic and cyrillic >= max(latin, arabic):
        return "ru"
    if arabic and arabic >= latin:
        characters = set(text)
        if characters & _PERSIAN_ONLY or "\u06cc" in text or "\u06a9" in text:
            return "fa"
        words = set(re.findall(r"[\u0600-\u06ff]+", text))
        if words & _PERSIAN_WORDS:
            return "fa"
        if (
            characters & _ARABIC_ONLY
            or _AR_DIACRITICS.search(text)
            or "\u064a" in text
            or "\u0643" in text
        ):
            return "ar"
        if words & _ARABIC_WORDS:
            return "ar"
        # Bare shared-script vocabulary with no distinguishing marker. Persian
        # remains the default so short Persian questions are not mislabelled.
        return "fa"
    words = _latin_words(text)
    german = len(words & _GERMAN_HINTS)
    french = len(words & _FRENCH_HINTS)
    english = len(words & _ENGLISH_HINTS)
    if any(marker in text for marker in ("ß", "ä", "ö", "ü")):
        german += 1
    if any(marker in text for marker in ("é", "è", "ê", "à", "ç", "œ", "î", "ô", "û")):
        french += 1
    if german > english and german >= french:
        return "de"
    if french > english and french >= german:
        return "fr"
    if english:
        return "en"
    # A short Latin token such as a project name: use the default language.
    return default


def detect_question_locale(value: str, *, default: str = DEFAULT_LOCALE) -> str:
    return detect_locale(value, default=default)


def resolve_response_locale(
    *,
    requested: object = None,
    question: str = "",
    profile_locale: object = None,
    default: str = DEFAULT_LOCALE,
) -> str:
    """Resolve the answer language without silently mixing languages.

    Precedence: an explicit per-request language, then the user's saved
    preference, then the detected question language, then the product default.
    """

    for candidate in (requested, profile_locale):
        if candidate is not None and str(candidate).strip():
            resolved = canonical_locale(candidate, default=None)
            if resolved is not None:
                return resolved
            if requested is candidate:
                raise KnowledgeError("KNOWLEDGE_LOCALE_UNSUPPORTED")
    detected = detect_locale(question, default=default)
    return canonical_locale(detected, default=default) or default


def localized_join(locale: object, values: Iterable[str]) -> str:
    separator = "، " if canonical_locale(locale, default="en") in {"fa", "ar"} else ", "
    return separator.join(value for value in values if value)


def text_direction(locale: object) -> Mapping[str, object]:
    definition = locale_definition(locale)
    return {
        "locale": None if definition is None else definition.locale,
        "direction": "ltr" if definition is None else definition.direction,
        "rtl": False if definition is None else definition.is_rtl,
        "script": None if definition is None else definition.script,
    }


__all__ = [
    "DEFAULT_LOCALE",
    "FALLBACK_LOCALE",
    "LOCALES",
    "RTL_LOCALES",
    "SOURCE_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "SUPPORTED_LANGUAGE_CODES",
    "SUPPORTED_LOCALES",
    "LocaleDefinition",
    "canonical_locale",
    "detect_locale",
    "detect_question_locale",
    "direction",
    "is_rtl",
    "language_code",
    "locale_definition",
    "locale_registry",
    "localized_join",
    "require_locale",
    "resolve_response_locale",
    "supported_locale",
    "text_direction",
]

SUPPORTED_LANGUAGES = SUPPORTED_LANGUAGE_CODES
