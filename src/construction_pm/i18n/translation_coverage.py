from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class TranslationCoverage:
    language: str
    required_keys: int
    translated_keys: int
    missing_keys: tuple[str, ...]
    orphan_keys: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_keys and not self.orphan_keys


def validate_translation_coverage(base: Mapping[str, str], translated: Mapping[str, str], *, language: str) -> TranslationCoverage:
    required = set(base)
    actual = set(translated)
    missing = tuple(sorted(required - actual))
    orphan = tuple(sorted(actual - required))
    invalid = [key for key, value in translated.items() if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip()]
    if invalid:
        raise ValueError("invalid translation entries: " + ", ".join(sorted(map(str, invalid))))
    return TranslationCoverage(language=language, required_keys=len(required), translated_keys=len(actual), missing_keys=missing, orphan_keys=orphan)


def assert_translation_complete(base: Mapping[str, str], translated: Mapping[str, str], *, language: str) -> TranslationCoverage:
    coverage = validate_translation_coverage(base, translated, language=language)
    if not coverage.complete:
        details = []
        if coverage.missing_keys: details.append("missing=" + ",".join(coverage.missing_keys))
        if coverage.orphan_keys: details.append("orphan=" + ",".join(coverage.orphan_keys))
        raise ValueError(f"incomplete translation for {language}: " + " ".join(details))
    return coverage
