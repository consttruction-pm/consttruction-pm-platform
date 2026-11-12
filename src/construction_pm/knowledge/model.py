"""Versioned contracts for the CUBI engineering knowledge base and assistant.

These records are deliberately transport-neutral and free of any third-party
model/provider concept. Everything here is deterministic, serializable and
validated on construction so a partially extracted or fabricated record cannot
be persisted or published.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Mapping, Sequence

EXTRACTION_VERSION = 1
MAX_TITLE_CHARS = 300
MAX_BLOCK_CHARS = 12_000
MAX_CARD_STEPS = 60
MAX_CITATIONS = 12
MAX_SEARCH_RESULTS = 50
MAX_TEXT_CHARS = 200_000


class KnowledgeError(ValueError):
    """Raised when a knowledge record violates its versioned contract."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        raise KnowledgeError("KNOWLEDGE_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    return moment.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise KnowledgeError("KNOWLEDGE_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None:
        raise KnowledgeError("KNOWLEDGE_TIMESTAMP_INVALID")
    return parsed


def sha256_hex(value: str) -> str:
    if not isinstance(value, str):
        raise KnowledgeError("KNOWLEDGE_HASH_INPUT_INVALID")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def text(value: object, code: str, *, maximum: int = MAX_TITLE_CHARS) -> str:
    if not isinstance(value, str):
        raise KnowledgeError(code)
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > maximum:
        raise KnowledgeError(code)
    return normalized


def optional_text(value: object, code: str, *, maximum: int = MAX_TITLE_CHARS) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise KnowledgeError(code)
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise KnowledgeError(code)
    return normalized


def _string_tuple(value: object, code: str, *, maximum_items: int = 200) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or len(value) > maximum_items:
        raise KnowledgeError(code)
    normalized: list[str] = []
    for item in value:
        normalized.append(text(item, code, maximum=MAX_BLOCK_CHARS))
    return tuple(normalized)


def normalize_language(value: object, default: str = "en") -> str:
    """Deterministic script-based language identification for declared languages."""

    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    if not isinstance(value, str):
        raise KnowledgeError("KNOWLEDGE_LANGUAGE_INVALID")
    if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", value.strip()):
        raise KnowledgeError("KNOWLEDGE_LANGUAGE_INVALID")
    return value.strip().lower()


_PERSIAN_RANGE = re.compile(r"[\u0600-\u06FF]")
_LATIN_RANGE = re.compile(r"[A-Za-z]")
_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_ARABIC_FORMS = {
    "ي": "ی",
    "ى": "ی",
    "ئ": "ی",
    "ك": "ک",
    "ۀ": "ه",
    "ﻻ": "لا",
    "ٱ": "ا",
}


def normalize_terms(value: str) -> str:
    """Unicode/Persian-aware normalization used by search and command matching.

    The original text is always preserved elsewhere; this form is only used for
    deterministic matching so that ``ك``/``ک``, Arabic-Indic digits, diacritics
    and tatweel do not create artificial misses.
    """

    if not isinstance(value, str):
        raise KnowledgeError("KNOWLEDGE_QUERY_INVALID")
    normalized = unicodedata.normalize("NFKC", value).translate(_DIGIT_MAP)
    normalized = "".join(
        _ARABIC_FORMS.get(character, character)
        for character in normalized
        if not unicodedata.combining(character) and character != "\u0640"
    )
    normalized = re.sub(r"[^\w\u0600-\u06FF\s]+", " ", normalized)
    # Arabic-script punctuation shares the block with letters; it is never part
    # of a searchable term.
    normalized = re.sub(r"[\u060C\u061B\u061F\u066A-\u066D\u06D4\u200c\u200d]+", " ", normalized)
    return " ".join(normalized.lower().split())


def detect_language(value: str) -> str:
    """Compatibility entry point for script-based locale identification.

    The full ten-locale detector lives in :mod:`construction_pm.knowledge.locales`;
    it is imported lazily to keep the model module dependency-free at import
    time. Existing callers that only distinguish Persian and English keep
    working, while Russian, Arabic, Chinese, Japanese, Korean, German and French
    are now identified as well.
    """

    if not isinstance(value, str):
        raise KnowledgeError("KNOWLEDGE_LANGUAGE_INVALID")
    persian = len(_PERSIAN_RANGE.findall(value))
    latin = len(_LATIN_RANGE.findall(value))
    if not persian and not latin:
        from .locales import detect_locale

        return detect_locale(value)
    if persian and persian >= latin:
        from .locales import detect_locale

        return detect_locale(value, default="fa")
    from .locales import detect_locale

    return detect_locale(value)


class SourceKind(str, Enum):
    HELP = "help"
    USER_GUIDE = "user_guide"
    HTML_HELP = "html_help"
    DOCUMENTATION_HOME = "documentation_home"
    DOCUMENT_INDEX = "document_index"


class TopicStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    PARSED = "parsed"
    VALIDATED = "validated"
    CONVERTED = "converted"
    PUBLISHED = "published"
    FAILED = "failed"


TERMINAL_TOPIC_STATUSES = frozenset(
    {TopicStatus.CONVERTED.value, TopicStatus.PUBLISHED.value}
)


class CardType(str, Enum):
    TRAINING = "training"
    OPERATION = "operation"
    CONFIGURATION = "configuration"
    CONCEPT = "concept"
    WORKFLOW = "workflow"
    TROUBLESHOOTING = "troubleshooting"
    LIMITATION = "limitation"
    RELATIONSHIP = "relationship"
    DECISION = "decision"
    REFERENCE = "reference"


class CardStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    REJECTED = "rejected"
    RETIRED = "retired"


class TranslationStatus(str, Enum):
    """Per-locale translation lifecycle; independent for every locale."""

    MISSING = "missing"
    DRAFT = "draft"
    TRANSLATED = "translated"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    PUBLISHED = "published"
    RETIRED = "retired"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TranslationSource(str, Enum):
    OFFICIAL_SOURCE = "official_source"
    CUBI_AUTHORED = "cubi_authored"
    HUMAN = "human"
    MACHINE = "machine"
    IMPORTED = "imported"


class KnowledgeScope(str, Enum):
    CENTRAL = "central"
    PROJECT = "project"
    USER_MEMORY = "user_memory"


class AssistantMode(str, Enum):
    TRAINING = "training"
    GUIDE = "guide"
    EXECUTE = "execute"


class WorkflowStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    title: str
    kind: SourceKind
    release: str
    landing_url: str
    toc_url: str | None
    publisher: str = "Official Version 26 reference"

    def validate(self) -> None:
        for name, value in (
            ("source_id", self.source_id),
            ("title", self.title),
            ("release", self.release),
            ("landing_url", self.landing_url),
            ("publisher", self.publisher),
        ):
            text(value, f"KNOWLEDGE_SOURCE_{name.upper()}_INVALID")
        if not self.landing_url.startswith("https://"):
            raise KnowledgeError("KNOWLEDGE_SOURCE_URL_MUST_BE_HTTPS")
        if self.toc_url is not None and not self.toc_url.startswith("https://"):
            raise KnowledgeError("KNOWLEDGE_SOURCE_URL_MUST_BE_HTTPS")
        if not isinstance(self.kind, SourceKind):
            raise KnowledgeError("KNOWLEDGE_SOURCE_KIND_INVALID")


@dataclass(frozen=True)
class TopicLink:
    """One entry discovered in an official table of contents."""

    topic_key: str
    url: str
    title: str
    depth: int
    order: int
    parent_key: str | None = None

    def validate(self) -> None:
        if not isinstance(self.topic_key, str) or not self.topic_key.strip():
            raise KnowledgeError("KNOWLEDGE_TOPIC_KEY_INVALID")
        if not isinstance(self.url, str) or not self.url.startswith("https://"):
            raise KnowledgeError("KNOWLEDGE_TOPIC_URL_INVALID")
        text(self.title, "KNOWLEDGE_TOPIC_TITLE_INVALID")
        if isinstance(self.depth, bool) or not isinstance(self.depth, int) or self.depth < 0:
            raise KnowledgeError("KNOWLEDGE_TOPIC_DEPTH_INVALID")
        if isinstance(self.order, bool) or not isinstance(self.order, int) or self.order < 0:
            raise KnowledgeError("KNOWLEDGE_TOPIC_ORDER_INVALID")


@dataclass(frozen=True)
class ContentBlock:
    kind: str
    text: str
    section: str | None = None
    level: int | None = None
    ordinal: int | None = None

    ALLOWED_KINDS = frozenset({"paragraph", "bullet", "step", "heading", "table", "note"})

    def validate(self) -> None:
        if self.kind not in self.ALLOWED_KINDS:
            raise KnowledgeError("KNOWLEDGE_BLOCK_KIND_INVALID")
        text(self.text, "KNOWLEDGE_BLOCK_TEXT_INVALID", maximum=MAX_BLOCK_CHARS)
        if self.section is not None:
            text(self.section, "KNOWLEDGE_BLOCK_SECTION_INVALID")
        for name, value in (("level", self.level), ("ordinal", self.ordinal)):
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise KnowledgeError(f"KNOWLEDGE_BLOCK_{name.upper()}_INVALID")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "kind": self.kind,
            "text": self.text,
            "section": self.section,
            "level": self.level,
            "ordinal": self.ordinal,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ContentBlock":
        if not isinstance(value, Mapping) or set(value) != {"kind", "text", "section", "level", "ordinal"}:
            raise KnowledgeError("KNOWLEDGE_BLOCK_INVALID")
        return cls(
            kind=str(value["kind"]),
            text=str(value["text"]),
            section=None if value["section"] is None else str(value["section"]),
            level=None if value["level"] is None else int(value["level"]),  # type: ignore[arg-type]
            ordinal=None if value["ordinal"] is None else int(value["ordinal"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class ParsedTopic:
    topic_id: str
    source_id: str
    topic_key: str
    url: str
    title: str
    language: str
    content_hash: str
    parent_key: str | None = None
    breadcrumb: tuple[str, ...] = ()
    headings: tuple[tuple[int, str], ...] = ()
    blocks: tuple[ContentBlock, ...] = ()
    steps: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    options: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    word_count: int = 0

    def validate(self) -> None:
        for name, value in (
            ("topic_id", self.topic_id),
            ("source_id", self.source_id),
            ("topic_key", self.topic_key),
            ("title", self.title),
            ("content_hash", self.content_hash),
        ):
            text(value, f"KNOWLEDGE_TOPIC_{name.upper()}_INVALID")
        if not self.url.startswith("https://"):
            raise KnowledgeError("KNOWLEDGE_TOPIC_URL_INVALID")
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_hash):
            raise KnowledgeError("KNOWLEDGE_TOPIC_HASH_INVALID")
        normalize_language(self.language)
        if not self.blocks:
            raise KnowledgeError("KNOWLEDGE_TOPIC_CONTENT_EMPTY")
        for block in self.blocks:
            block.validate()
        if len(self.steps) > MAX_CARD_STEPS:
            raise KnowledgeError("KNOWLEDGE_TOPIC_TOO_MANY_STEPS")
        for item in (
            self.steps,
            self.prerequisites,
            self.warnings,
            self.options,
            self.limitations,
            self.related,
        ):
            _string_tuple(item, "KNOWLEDGE_TOPIC_LIST_INVALID")
        if isinstance(self.word_count, bool) or not isinstance(self.word_count, int) or self.word_count < 0:
            raise KnowledgeError("KNOWLEDGE_TOPIC_WORD_COUNT_INVALID")

    def searchable_text(self) -> str:
        parts = [self.title, " ".join(self.breadcrumb)]
        parts.extend(block.text for block in self.blocks)
        return "\n".join(part for part in parts if part)


@dataclass(frozen=True)
class KnowledgeCard:
    card_id: str
    card_type: CardType
    title: str
    category: str
    purpose: str
    steps: tuple[str, ...]
    prerequisites: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    relations: tuple[str, ...]
    source_url: str
    source_title: str
    source_version: str
    extracted_at: datetime
    validation_status: CardStatus
    publication_status: CardStatus
    content_hash: str
    topic_id: str | None = None
    scope: KnowledgeScope = KnowledgeScope.CENTRAL
    tenant_id: str | None = None
    project_id: str | None = None
    reviewer: str | None = None
    published_at: datetime | None = None
    revision: int = 0

    def validate(self) -> None:
        text(self.card_id, "KNOWLEDGE_CARD_ID_INVALID", maximum=64)
        if not isinstance(self.card_type, CardType):
            raise KnowledgeError("KNOWLEDGE_CARD_TYPE_INVALID")
        text(self.title, "KNOWLEDGE_CARD_TITLE_INVALID")
        text(self.category, "KNOWLEDGE_CARD_CATEGORY_INVALID")
        text(self.purpose, "KNOWLEDGE_CARD_PURPOSE_INVALID", maximum=MAX_BLOCK_CHARS)
        for name, value in (
            ("steps", self.steps),
            ("prerequisites", self.prerequisites),
            ("inputs", self.inputs),
            ("outputs", self.outputs),
            ("warnings", self.warnings),
            ("limitations", self.limitations),
            ("relations", self.relations),
        ):
            _string_tuple(value, f"KNOWLEDGE_CARD_{name.upper()}_INVALID")
        if len(self.steps) > MAX_CARD_STEPS:
            raise KnowledgeError("KNOWLEDGE_CARD_TOO_MANY_STEPS")
        if not self.source_url.startswith("https://"):
            raise KnowledgeError("KNOWLEDGE_CARD_SOURCE_URL_INVALID")
        text(self.source_title, "KNOWLEDGE_CARD_SOURCE_TITLE_INVALID")
        text(self.source_version, "KNOWLEDGE_CARD_SOURCE_VERSION_INVALID")
        if not isinstance(self.extracted_at, datetime) or self.extracted_at.tzinfo is None:
            raise KnowledgeError("KNOWLEDGE_CARD_EXTRACTED_AT_INVALID")
        if self.publication_status is CardStatus.PUBLISHED:
            self.assert_publishable()
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_hash):
            raise KnowledgeError("KNOWLEDGE_CARD_HASH_INVALID")
        if self.scope is not KnowledgeScope.CENTRAL and (
            not self.tenant_id or not self.project_id
        ):
            raise KnowledgeError("KNOWLEDGE_CARD_SCOPE_INCOMPLETE")
        if self.revision < 0:
            raise KnowledgeError("KNOWLEDGE_CARD_REVISION_INVALID")

    def assert_publishable(self) -> None:
        """A card without a real source, evidence and complete steps cannot ship."""

        if not self.source_url.startswith("https://") or not self.source_title.strip():
            raise KnowledgeError("KNOWLEDGE_CARD_SOURCE_REQUIRED")
        if self.validation_status is not CardStatus.VALIDATED:
            raise KnowledgeError("KNOWLEDGE_CARD_NOT_VALIDATED")
        if not self.reviewer or not self.reviewer.strip():
            raise KnowledgeError("KNOWLEDGE_CARD_REVIEWER_REQUIRED")
        if self.published_at is None:
            raise KnowledgeError("KNOWLEDGE_CARD_PUBLICATION_TIME_REQUIRED")
        if self.card_type is CardType.OPERATION and not self.steps:
            raise KnowledgeError("KNOWLEDGE_CARD_OPERATION_STEPS_REQUIRED")
        if not self.purpose.strip():
            raise KnowledgeError("KNOWLEDGE_CARD_PURPOSE_REQUIRED")


@dataclass(frozen=True)
class LanguageContext:
    """Every language field a client needs to render one response correctly.

    ``question_language`` and ``response_language`` are request-scoped; the
    remaining fields describe the selected content version. Keeping them in one
    record prevents a UI from guessing the direction or hiding a missing
    translation.
    """

    locale: str
    language_code: str
    source_language: str
    question_language: str
    response_language: str
    default_language: str
    fallback_language: str
    direction: str
    translation_status: str
    review_status: str
    published_language_version: int | None = None
    technical_glossary: tuple[tuple[str, str], ...] = ()
    localization_metadata: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "locale": self.locale,
            "language_code": self.language_code,
            "source_language": self.source_language,
            "question_language": self.question_language,
            "response_language": self.response_language,
            "default_language": self.default_language,
            "fallback_language": self.fallback_language,
            "direction": self.direction,
            "translation_status": self.translation_status,
            "review_status": self.review_status,
            "published_language_version": self.published_language_version,
            "technical_glossary": [
                {"term": term, "definition": definition}
                for term, definition in self.technical_glossary
            ],
            "localization_metadata": dict(self.localization_metadata),
        }


@dataclass(frozen=True)
class TranslationRecord:
    """Localized content for one Knowledge Card in one locale.

    The record is the unit of translation, review and publication. A card can be
    published in English while every other locale is still ``missing``; nothing
    in this model cascades a publication across locales.
    """

    card_id: str
    locale: str
    language_code: str
    source_language: str
    title: str
    summary: str
    body: str
    steps: tuple[str, ...]
    prerequisites: tuple[str, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    relations: tuple[str, ...]
    glossary: tuple[tuple[str, str], ...]
    source_note: str
    translation_status: TranslationStatus
    review_status: ReviewStatus
    translation_version: int
    published_language_version: int | None
    translation_source: TranslationSource
    machine_translated: bool
    localization_metadata: Mapping[str, object]
    content_hash: str
    updated_at: datetime
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    published_at: datetime | None = None

    def validate(self) -> None:
        from .locales import canonical_locale, language_code as locale_language_code, require_locale

        text(self.card_id, "KNOWLEDGE_TRANSLATION_CARD_ID_INVALID", maximum=64)
        require_locale(self.locale, code="KNOWLEDGE_TRANSLATION_LOCALE_UNSUPPORTED")
        if self.locale != canonical_locale(self.locale, default=None):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_LOCALE_NOT_CANONICAL")
        if self.language_code != locale_language_code(self.locale):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_LANGUAGE_CODE_MISMATCH")
        normalize_language(self.source_language)
        if not isinstance(self.translation_status, TranslationStatus):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_STATUS_INVALID")
        if not isinstance(self.review_status, ReviewStatus):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_REVIEW_STATUS_INVALID")
        if not isinstance(self.translation_source, TranslationSource):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_SOURCE_INVALID")
        if isinstance(self.translation_version, bool) or not isinstance(self.translation_version, int) or self.translation_version < 0:
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_VERSION_INVALID")
        if self.published_language_version is not None and (
            isinstance(self.published_language_version, bool)
            or not isinstance(self.published_language_version, int)
            or self.published_language_version < 1
        ):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_PUBLISHED_VERSION_INVALID")
        if not isinstance(self.machine_translated, bool):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_MACHINE_FLAG_INVALID")
        if not isinstance(self.localization_metadata, Mapping):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_METADATA_INVALID")
        for name, value in (
            ("steps", self.steps),
            ("prerequisites", self.prerequisites),
            ("warnings", self.warnings),
            ("limitations", self.limitations),
            ("relations", self.relations),
        ):
            _string_tuple(value, f"KNOWLEDGE_TRANSLATION_{name.upper()}_INVALID")
        if len(self.steps) > MAX_CARD_STEPS:
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_TOO_MANY_STEPS")
        if self.glossary:
            for pair in self.glossary:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    raise KnowledgeError("KNOWLEDGE_TRANSLATION_GLOSSARY_INVALID")
                text(pair[0], "KNOWLEDGE_TRANSLATION_GLOSSARY_INVALID")
                text(pair[1], "KNOWLEDGE_TRANSLATION_GLOSSARY_INVALID", maximum=MAX_BLOCK_CHARS)
        if self.content_hash and not re.fullmatch(r"[0-9a-f]{64}", self.content_hash):
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_HASH_INVALID")
        if not isinstance(self.updated_at, datetime) or self.updated_at.tzinfo is None:
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_UPDATED_AT_INVALID")
        if self.translation_status is TranslationStatus.MISSING:
            return
        text(self.title, "KNOWLEDGE_TRANSLATION_TITLE_INVALID")
        text(self.summary, "KNOWLEDGE_TRANSLATION_SUMMARY_INVALID", maximum=MAX_BLOCK_CHARS)
        if len(self.body) > MAX_TEXT_CHARS:
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_BODY_INVALID")
        if not self.content_hash:
            raise KnowledgeError("KNOWLEDGE_TRANSLATION_HASH_REQUIRED")
        if self.translation_status in {
            TranslationStatus.APPROVED,
            TranslationStatus.PUBLISHED,
        }:
            if self.review_status is not ReviewStatus.APPROVED or not self.reviewer:
                raise KnowledgeError("KNOWLEDGE_TRANSLATION_REVIEW_REQUIRED")
            if self.machine_translated:
                raise KnowledgeError("KNOWLEDGE_TRANSLATION_MACHINE_OUTPUT_CANNOT_BE_APPROVED")
        if self.translation_status is TranslationStatus.PUBLISHED:
            if self.reviewed_at is None or self.published_at is None:
                raise KnowledgeError("KNOWLEDGE_TRANSLATION_PUBLICATION_TIME_REQUIRED")
            if self.published_language_version is None:
                raise KnowledgeError("KNOWLEDGE_TRANSLATION_PUBLISHED_VERSION_REQUIRED")
            if self.source_language == self.locale:
                raise KnowledgeError("KNOWLEDGE_TRANSLATION_SOURCE_LOCALE_CANNOT_BE_TRANSLATED")

    def available(self) -> bool:
        return self.translation_status not in {
            TranslationStatus.MISSING,
            TranslationStatus.RETIRED,
        }

    def approved_for_answer(self) -> bool:
        """Only reviewed, approved/published content may answer a question."""

        return (
            self.translation_status in {TranslationStatus.APPROVED, TranslationStatus.PUBLISHED}
            and self.review_status is ReviewStatus.APPROVED
            and not self.machine_translated
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "card_id": self.card_id,
            "locale": self.locale,
            "language_code": self.language_code,
            "source_language": self.source_language,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "steps": list(self.steps),
            "prerequisites": list(self.prerequisites),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
            "relations": list(self.relations),
            "technical_glossary": [
                {"term": term, "definition": definition} for term, definition in self.glossary
            ],
            "source_note": self.source_note,
            "translation_status": self.translation_status.value,
            "review_status": self.review_status.value,
            "translation_version": self.translation_version,
            "published_language_version": self.published_language_version,
            "translation_source": self.translation_source.value,
            "machine_translated": self.machine_translated,
            "localization_metadata": dict(self.localization_metadata),
            "content_hash": self.content_hash,
            "reviewer": self.reviewer,
            "reviewed_at": None if self.reviewed_at is None else iso(self.reviewed_at),
            "published_at": None if self.published_at is None else iso(self.published_at),
            "updated_at": iso(self.updated_at),
        }


def translation_content_hash(record: TranslationRecord) -> str:
    payload = "|".join(
        (
            record.card_id,
            record.locale,
            record.title,
            record.summary,
            record.body,
            "\n".join(record.steps),
            "\n".join(record.prerequisites),
            "\n".join(record.warnings),
            "\n".join(record.limitations),
            "\n".join(record.relations),
            "\n".join(f"{term}={definition}" for term, definition in record.glossary),
            record.source_note,
            str(record.translation_version),
        )
    )
    return sha256_hex(payload)


@dataclass(frozen=True)
class SearchScope:
    """Trusted retrieval scope resolved by the application, never by a client claim."""

    user_id: str
    tenant_id: str | None = None
    project_id: str | None = None
    include_central: bool = True
    include_project: bool = True
    include_user_memory: bool = True

    def validate(self) -> None:
        text(self.user_id, "KNOWLEDGE_SCOPE_USER_REQUIRED")
        for name, value in (("tenant_id", self.tenant_id), ("project_id", self.project_id)):
            if value is not None:
                text(value, f"KNOWLEDGE_SCOPE_{name.upper()}_INVALID")
        if (self.include_project or self.include_user_memory) and (
            not self.tenant_id or not self.project_id
        ):
            raise KnowledgeError("KNOWLEDGE_SCOPE_PROJECT_REQUIRED")


@dataclass(frozen=True)
class SearchHit:
    entity_kind: str
    entity_id: str
    title: str
    snippet: str
    score: float
    scope: KnowledgeScope
    source_url: str | None = None
    card_type: str | None = None
    card_id: str | None = None
    language: str | None = None
    source_language: str | None = None
    translation_status: str | None = None
    translation_available: bool | None = None
    fallback_used: bool = False
    matched_terms: tuple[str, ...] = ()
    matched_fields: tuple[str, ...] = ()
    evidence: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "entity_kind": self.entity_kind,
            "entity_id": self.entity_id,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "scope": self.scope.value,
            "source_url": self.source_url,
            "card_type": self.card_type,
            "card_id": self.card_id,
            "language": self.language,
            "source_language": self.source_language,
            "translation_status": self.translation_status,
            "translation_available": self.translation_available,
            "fallback_used": self.fallback_used,
            "matched_terms": list(self.matched_terms),
            "matched_fields": list(self.matched_fields),
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class SearchOutcome:
    query: str
    hits: tuple[SearchHit, ...]
    insufficient_knowledge: bool
    query_locale: str | None = None
    response_locale: str | None = None
    filters: Mapping[str, object] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.query, str) or not self.query.strip():
            raise KnowledgeError("KNOWLEDGE_SEARCH_QUERY_REQUIRED")
        if len(self.hits) > MAX_SEARCH_RESULTS:
            raise KnowledgeError("KNOWLEDGE_SEARCH_TOO_MANY_RESULTS")
        if not isinstance(self.insufficient_knowledge, bool):
            raise KnowledgeError("KNOWLEDGE_SEARCH_FLAG_INVALID")


@dataclass(frozen=True)
class Citation:
    title: str
    source_url: str
    card_id: str | None = None
    source_version: str | None = None


@dataclass(frozen=True)
class AssistantAnswer:
    kind: str
    message: str
    mode: AssistantMode
    language: str
    citations: tuple[Citation, ...] = ()
    card_ids: tuple[str, ...] = ()
    steps: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    next_step: str | None = None
    insufficient_knowledge: bool = False
    workflow_run_id: str | None = None
    workflow_step: str | None = None
    source_language: str | None = None
    response_language: str | None = None
    content_language: str | None = None
    translation_status: str | None = None
    fallback_used: bool = False
    language_context: LanguageContext | None = None

    def validate(self) -> None:
        if self.kind not in {"answer", "knowledge_gap", "clarification", "workflow_step", "action_result"}:
            raise KnowledgeError("KNOWLEDGE_ANSWER_KIND_INVALID")
        if not isinstance(self.message, str) or not self.message.strip():
            raise KnowledgeError("KNOWLEDGE_ANSWER_MESSAGE_INVALID")
        if len(self.citations) > MAX_CITATIONS:
            raise KnowledgeError("KNOWLEDGE_ANSWER_TOO_MANY_CITATIONS")
        if self.insufficient_knowledge and self.kind == "answer":
            raise KnowledgeError("KNOWLEDGE_ANSWER_GAP_FLAG_INVALID")
        normalize_language(self.language)

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "kind": self.kind,
            "message": self.message,
            "mode": self.mode.value,
            "language": self.language,
            "citations": [
                {
                    "title": citation.title,
                    "source_url": citation.source_url,
                    "card_id": citation.card_id,
                    "source_version": citation.source_version,
                }
                for citation in self.citations
            ],
            "card_ids": list(self.card_ids),
            "steps": list(self.steps),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
            "next_step": self.next_step,
            "insufficient_knowledge": self.insufficient_knowledge,
            "workflow_run_id": self.workflow_run_id,
            "workflow_step": self.workflow_step,
            "source_language": self.source_language,
            "response_language": self.response_language,
            "content_language": self.content_language,
            "translation_status": self.translation_status,
            "fallback_used": self.fallback_used,
            "language_context": (
                None if self.language_context is None else self.language_context.as_dict()
            ),
        }


def card_id_for(source_id: str, topic_key: str, card_type: CardType) -> str:
    seed = f"{source_id}:{topic_key}:{card_type.value}"
    return "KC-" + sha256_hex(seed)[:24]


def topic_id_for(source_id: str, topic_key: str) -> str:
    return "KT-" + sha256_hex(f"{source_id}:{topic_key}")[:24]


def card_content_hash(card: KnowledgeCard) -> str:
    payload = "|".join(
        (
            card.card_type.value,
            card.title,
            card.category,
            card.purpose,
            "\n".join(card.steps),
            "\n".join(card.prerequisites),
            "\n".join(card.inputs),
            "\n".join(card.outputs),
            "\n".join(card.warnings),
            "\n".join(card.limitations),
            card.source_url,
            card.source_version,
        )
    )
    return sha256_hex(payload)


def merge_unique(items: Iterable[str], *, limit: int = 200) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = " ".join(str(item).split())
        key = normalize_terms(normalized)
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
        if len(result) >= limit:
            break
    return tuple(result)


__all__ = [
    "AssistantAnswer",
    "AssistantMode",
    "CardStatus",
    "CardType",
    "Citation",
    "ContentBlock",
    "EXTRACTION_VERSION",
    "KnowledgeCard",
    "KnowledgeError",
    "KnowledgeScope",
    "LanguageContext",
    "ParsedTopic",
    "ReviewStatus",
    "SearchHit",
    "SearchOutcome",
    "SearchScope",
    "SourceDefinition",
    "SourceKind",
    "TERMINAL_TOPIC_STATUSES",
    "TopicLink",
    "TopicStatus",
    "TranslationRecord",
    "TranslationSource",
    "TranslationStatus",
    "WorkflowStatus",
    "card_content_hash",
    "card_id_for",
    "detect_language",
    "iso",
    "merge_unique",
    "normalize_language",
    "normalize_terms",
    "optional_text",
    "parse_iso",
    "sha256_hex",
    "text",
    "topic_id_for",
    "utc_now",
]
