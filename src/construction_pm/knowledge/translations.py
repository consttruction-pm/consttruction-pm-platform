"""Per-locale translation lifecycle for Knowledge Cards.

Translation is not a property of a card as a whole. Every locale owns an
independent record with its own content, version, review state and publication
state. Publishing Russian never publishes Persian, and a locale with no record
is reported as ``missing`` rather than silently replaced by the source language.

The module contains no translation service call. Content arrives through the
API from a human contributor, a CUBI-authored seed or a reviewed import; the
only thing this layer guarantees is that unreviewed content cannot be
published and machine output cannot be approved.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Mapping, Sequence

from .locales import (
    DEFAULT_LOCALE,
    FALLBACK_LOCALE,
    LEGACY_LOCALES,
    PRODUCT_LOCALES,
    SOURCE_LANGUAGE,
    SUPPORTED_LOCALES,
    TARGET_LOCALES,
    canonical_locale,
    detect_locale,
    language_code,
    require_locale,
    translation_locale_candidates,
)
from .model import (
    CardStatus,
    KnowledgeCard,
    KnowledgeError,
    ReviewStatus,
    TranslationRecord,
    TranslationSource,
    TranslationStatus,
    iso,
    translation_content_hash,
    utc_now,
)
from .store import KnowledgeStore

_REQUIRED_FIELDS = ("title", "summary")


class TranslationError(KnowledgeError):
    """Raised when a translation transition would misrepresent content."""


def source_record(card: KnowledgeCard, *, updated_at: datetime | None = None) -> TranslationRecord:
    """Represent the official English card as the source-language record.

    This is a read-time projection, not a stored translation. Its status mirrors
    the card's own publication state so a client can never show a draft source as
    published.
    """

    moment = updated_at or card.extracted_at
    published = card.publication_status is CardStatus.PUBLISHED
    status = TranslationStatus.PUBLISHED if published else TranslationStatus.DRAFT
    return TranslationRecord(
        card_id=card.card_id,
        locale=DEFAULT_LOCALE,
        language_code=language_code(DEFAULT_LOCALE),
        source_language=SOURCE_LANGUAGE,
        title=card.title,
        summary=card.purpose,
        body="\n".join(step for step in card.steps),
        steps=tuple(card.steps),
        prerequisites=tuple(card.prerequisites),
        warnings=tuple(card.warnings),
        limitations=tuple(card.limitations),
        relations=tuple(card.relations),
        glossary=(),
        source_note=f"Official Version {card.source_version} source",
        translation_status=status,
        review_status=ReviewStatus.APPROVED if published else ReviewStatus.PENDING,
        translation_version=max(1, card.revision + 1),
        published_language_version=(card.revision + 1) if published else None,
        translation_source=TranslationSource.OFFICIAL_SOURCE,
        machine_translated=False,
        localization_metadata={"source_url": card.source_url, "source_title": card.source_title},
        content_hash=card.content_hash,
        updated_at=card.published_at if published and card.published_at else moment,
        reviewer=card.reviewer,
        reviewed_at=card.published_at if published else None,
        published_at=card.published_at if published else None,
    )


def missing_record(
    card_id: str,
    locale: str,
    *,
    source_language: str = SOURCE_LANGUAGE,
    updated_at: datetime | None = None,
) -> TranslationRecord:
    resolved = require_locale(locale)
    return TranslationRecord(
        card_id=card_id,
        locale=resolved,
        language_code=language_code(resolved),
        source_language=source_language,
        title="",
        summary="",
        body="",
        steps=(),
        prerequisites=(),
        warnings=(),
        limitations=(),
        relations=(),
        glossary=(),
        source_note="",
        translation_status=TranslationStatus.MISSING,
        review_status=ReviewStatus.PENDING,
        translation_version=0,
        published_language_version=None,
        translation_source=TranslationSource.CUBI_AUTHORED,
        machine_translated=False,
        localization_metadata={},
        content_hash="",
        updated_at=updated_at or utc_now(),
    )


def localized_record(
    store: KnowledgeStore,
    card: KnowledgeCard,
    locale: str,
) -> TranslationRecord:
    resolved = require_locale(locale)
    if resolved == DEFAULT_LOCALE:
        return source_record(card)
    for candidate in translation_locale_candidates(resolved):
        stored = store.get_translation(card.card_id, candidate)
        if stored is not None:
            return _canonicalize_record(stored, resolved)
    return missing_record(card.card_id, resolved, updated_at=card.extracted_at)


def _canonicalize_record(record: TranslationRecord, locale: str) -> TranslationRecord:
    """Present a legacy-code row under the one canonical product locale.

    The stored row is left untouched. Only the in-memory view is normalized, and
    the content hash is recomputed so the record stays internally consistent if
    a reviewer later saves a new version under the canonical code.
    """

    normalized = replace(
        record,
        locale=locale,
        language_code=language_code(locale),
    )
    if record.locale == locale and record.language_code == normalized.language_code:
        return record
    return replace(normalized, content_hash=translation_content_hash(normalized))


def translation_coverage(
    store: KnowledgeStore, cards: Sequence[KnowledgeCard | str]
) -> dict[str, object]:
    """Measure every product locale against the full card set.

    The denominator is the number of cards that should be localized times the
    seven product translation targets. Chinese is one target: legacy ``zh-CN``
    and ``zh-TW`` rows for the same card collapse into a single ``zh-Hans``
    slot. Retired locales such as Russian are reported separately and never
    inflate the denominator.

    ``answerable`` applies the same rule the assistant uses — published card,
    approved non-machine translation whose source binding is current — so a
    coverage number can never promise an answer the retrieval path would refuse
    to give.
    """

    card_objects: list[KnowledgeCard] = []
    for item in cards:
        card = item if isinstance(item, KnowledgeCard) else store.get_card(str(item))
        if card is not None:
            card_objects.append(card)
    target_locales = list(TARGET_LOCALES)
    counts: dict[str, dict[str, int]] = {
        locale: {status.value: 0 for status in TranslationStatus}
        for locale in SUPPORTED_LOCALES
    }
    inventory: dict[str, dict[str, int | float]] = {
        locale: {
            "records": 0,
            "filled": 0,
            "published": 0,
            "approved": 0,
            "complete": 0,
            "answerable": 0,
            "machine_translated": 0,
            "stale_source_binding": 0,
            "missing_slots": 0,
        }
        for locale in target_locales
    }
    legacy_inventory: dict[str, dict[str, int]] = {
        code: {"records": 0, "published": 0, "approved": 0, "answerable": 0}
        for code in LEGACY_LOCALES
    }
    storage_codes: dict[str, int] = {}
    legacy_records = 0
    by_card: dict[str, dict[str, TranslationRecord]] = {}
    for card in card_objects:
        for record in store.list_translations(card.card_id):
            storage_codes[record.locale] = storage_codes.get(record.locale, 0) + 1
            canonical = canonical_locale(record.locale, default=record.locale)
            if canonical != record.locale:
                legacy_records += 1
            existing = by_card.setdefault(card.card_id, {}).get(canonical)
            if existing is None or _prefer_record(record, existing):
                by_card[card.card_id][canonical] = record
    for card in card_objects:
        records = by_card.get(card.card_id, {})
        for locale, record in records.items():
            if locale in counts:
                row = counts[locale]
                row[record.translation_status.value] = row.get(record.translation_status.value, 0) + 1
        for locale in target_locales:
            row = inventory[locale]
            record = records.get(locale)
            if record is None:
                row["missing_slots"] = int(row["missing_slots"]) + 1
                continue
            row["records"] = int(row["records"]) + 1
            if record.translation_status not in {
                TranslationStatus.MISSING,
                TranslationStatus.RETIRED,
            }:
                row["filled"] = int(row["filled"]) + 1
            if record.translation_status is TranslationStatus.PUBLISHED:
                row["published"] = int(row["published"]) + 1
            if record.translation_status is TranslationStatus.APPROVED:
                row["approved"] = int(row["approved"]) + 1
            if record.machine_translated:
                row["machine_translated"] = int(row["machine_translated"]) + 1
            if completeness(record, card_type=card.card_type.value)["complete"]:
                row["complete"] = int(row["complete"]) + 1
            if (
                card.publication_status is CardStatus.PUBLISHED
                and record.approved_for_answer()
                and not record.machine_translated
            ):
                if source_binding_current(card, record):
                    row["answerable"] = int(row["answerable"]) + 1
                else:
                    row["stale_source_binding"] = int(row["stale_source_binding"]) + 1
        for locale in LEGACY_LOCALES:
            record = records.get(locale)
            row = legacy_inventory.setdefault(
                locale, {"records": 0, "published": 0, "approved": 0, "answerable": 0}
            )
            if record is None:
                continue
            row["records"] += 1
            if record.translation_status is TranslationStatus.PUBLISHED:
                row["published"] += 1
            if record.translation_status is TranslationStatus.APPROVED:
                row["approved"] += 1
            if (
                card.publication_status is CardStatus.PUBLISHED
                and record.approved_for_answer()
                and not record.machine_translated
                and source_binding_current(card, record)
            ):
                row["answerable"] += 1
    total_cards = len(card_objects)
    available = total_cards * len(target_locales)
    filled = sum(int(row["filled"]) for row in inventory.values())
    published = sum(int(row["published"]) for row in inventory.values())
    approved = sum(int(row["approved"]) for row in inventory.values())
    return {
        "locales": counts,
        "cards": total_cards,
        "source_language": SOURCE_LANGUAGE,
        "product_locales": list(PRODUCT_LOCALES),
        "target_locales": target_locales,
        "legacy_locales": list(LEGACY_LOCALES),
        "available_slots": available,
        "filled_slots": filled,
        "published_slots": published,
        "approved_slots": approved,
        "missing_slots": available - filled,
        "coverage_percent": round(filled * 100.0 / available, 2) if available else 0.0,
        "inventory": inventory,
        "legacy": {
            "locales": list(LEGACY_LOCALES),
            "records": sum(int(row["records"]) for row in legacy_inventory.values()),
            "published": sum(int(row["published"]) for row in legacy_inventory.values()),
            "approved": sum(int(row["approved"]) for row in legacy_inventory.values()),
            "by_locale": legacy_inventory,
            "storage_codes": storage_codes,
            "normalized_records": legacy_records,
        },
    }


def _prefer_record(candidate: TranslationRecord, current: TranslationRecord) -> bool:
    """Choose one persisted row when legacy and canonical codes both exist."""

    rank = {
        TranslationStatus.PUBLISHED: 6,
        TranslationStatus.APPROVED: 5,
        TranslationStatus.TRANSLATED: 4,
        TranslationStatus.REVIEW_REQUIRED: 3,
        TranslationStatus.DRAFT: 2,
        TranslationStatus.RETIRED: 1,
        TranslationStatus.MISSING: 0,
    }
    candidate_key = (
        rank.get(candidate.translation_status, 0),
        candidate.translation_version,
        candidate.locale == canonical_locale(candidate.locale, default=candidate.locale),
    )
    current_key = (
        rank.get(current.translation_status, 0),
        current.translation_version,
        current.locale == canonical_locale(current.locale, default=current.locale),
    )
    return candidate_key > current_key


def completeness(record: TranslationRecord, *, card_type: str | None = None) -> dict[str, object]:
    missing: list[str] = []
    if record.translation_status is TranslationStatus.MISSING:
        missing.extend(["title", "summary", "body"])
    else:
        if not record.title.strip():
            missing.append("title")
        if not record.summary.strip():
            missing.append("summary")
        if card_type == "operation" and not record.steps:
            missing.append("steps")
    return {"complete": not missing, "missing_fields": missing}


def build_translation(
    card: KnowledgeCard,
    locale: str,
    payload: Mapping[str, object],
    *,
    actor_id: str,
    now: datetime,
    existing: TranslationRecord | None = None,
    requested_status: TranslationStatus | str | None = None,
) -> TranslationRecord:
    """Create or replace one locale record from contributor-supplied content."""

    if card.card_id != payload.get("card_id", card.card_id):
        raise TranslationError("KNOWLEDGE_TRANSLATION_CARD_MISMATCH")
    resolved = require_locale(locale)
    source = str(payload.get("translation_source") or TranslationSource.HUMAN.value)
    try:
        translation_source = TranslationSource(source)
    except ValueError as exc:
        raise TranslationError("KNOWLEDGE_TRANSLATION_SOURCE_INVALID") from exc
    if translation_source is TranslationSource.MACHINE:
        # Provenance wins over the client flag: machine output stays marked as
        # machine output even when the request claims it is human.
        machine = True
    else:
        machine = bool(payload.get("machine_translated", False))
    if requested_status is None:
        status = (
            TranslationStatus.DRAFT
            if not str(payload.get("title") or "").strip()
            else TranslationStatus.TRANSLATED
        )
    else:
        status = (
            requested_status
            if isinstance(requested_status, TranslationStatus)
            else TranslationStatus(str(requested_status))
        )
    if machine and status in {TranslationStatus.APPROVED, TranslationStatus.PUBLISHED}:
        raise TranslationError("KNOWLEDGE_TRANSLATION_MACHINE_OUTPUT_CANNOT_BE_APPROVED")
    version = 1 if existing is None else existing.translation_version + 1
    glossary_value = payload.get("technical_glossary") or payload.get("glossary") or []
    glossary: list[tuple[str, str]] = []
    if isinstance(glossary_value, Mapping):
        glossary = [(str(term), str(definition)) for term, definition in glossary_value.items()]
    elif isinstance(glossary_value, (list, tuple)):
        for item in glossary_value:
            if isinstance(item, Mapping):
                glossary.append((str(item.get("term", "")), str(item.get("definition", ""))))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                glossary.append((str(item[0]), str(item[1])))
    metadata = payload.get("localization_metadata")
    localization_metadata = dict(metadata) if isinstance(metadata, Mapping) else {}
    # The contributor identity and the origin of the text are part of the
    # translation record, not only of the surrounding audit entry.
    localization_metadata.setdefault("translator_id", actor_id)
    localization_metadata.setdefault("translated_at", now.isoformat())
    localization_metadata.setdefault("translation_source", translation_source.value)
    localization_metadata.setdefault("machine_translated", machine)
    record = TranslationRecord(
        card_id=card.card_id,
        locale=resolved,
        language_code=language_code(resolved),
        source_language=str(payload.get("source_language") or SOURCE_LANGUAGE),
        title=str(payload.get("title") or "").strip(),
        summary=str(payload.get("summary") or "").strip(),
        body=str(payload.get("body") or ""),
        steps=_string_list(payload.get("steps")),
        prerequisites=_string_list(payload.get("prerequisites")),
        warnings=_string_list(payload.get("warnings")),
        limitations=_string_list(payload.get("limitations")),
        relations=_string_list(payload.get("relations")),
        glossary=tuple(glossary),
        source_note=str(payload.get("source_note") or ""),
        translation_status=status,
        review_status=ReviewStatus.PENDING,
        translation_version=version,
        published_language_version=None,
        translation_source=translation_source,
        machine_translated=machine,
        localization_metadata=localization_metadata,
        content_hash="",
        updated_at=now,
        reviewer=None,
        reviewed_at=None,
        published_at=None,
    )
    record = replace(record, content_hash=translation_content_hash(record))
    record.validate()
    return record


def review_translation(
    record: TranslationRecord,
    *,
    reviewer: str,
    accept: bool,
    now: datetime,
) -> TranslationRecord:
    if not reviewer or not reviewer.strip():
        raise TranslationError("KNOWLEDGE_TRANSLATION_REVIEWER_REQUIRED")
    if record.translation_status is TranslationStatus.MISSING:
        raise TranslationError("KNOWLEDGE_TRANSLATION_MISSING")
    if accept and record.machine_translated:
        raise TranslationError("KNOWLEDGE_TRANSLATION_MACHINE_OUTPUT_CANNOT_BE_APPROVED")
    status = TranslationStatus.APPROVED if accept else TranslationStatus.REVIEW_REQUIRED
    reviewed = replace(
        record,
        translation_status=status,
        review_status=ReviewStatus.APPROVED if accept else ReviewStatus.REJECTED,
        reviewer=reviewer,
        reviewed_at=now if accept else None,
        published_language_version=None,
        published_at=None,
        # A review decision is a new persisted state, so it advances the
        # version. Otherwise two reviewers holding the same stale version could
        # overwrite each other's decision undetected.
        translation_version=record.translation_version + 1,
    )
    reviewed.validate()
    return reviewed


def publish_translation(
    card: KnowledgeCard,
    record: TranslationRecord,
    *,
    reviewer: str,
    now: datetime,
) -> TranslationRecord:
    if card.publication_status is not CardStatus.PUBLISHED:
        raise TranslationError("KNOWLEDGE_TRANSLATION_SOURCE_CARD_NOT_PUBLISHED")
    if record.translation_status is not TranslationStatus.APPROVED:
        raise TranslationError("KNOWLEDGE_TRANSLATION_NOT_APPROVED")
    if record.review_status is not ReviewStatus.APPROVED or not record.reviewer:
        raise TranslationError("KNOWLEDGE_TRANSLATION_REVIEW_REQUIRED")
    if record.machine_translated:
        raise TranslationError("KNOWLEDGE_TRANSLATION_MACHINE_OUTPUT_CANNOT_BE_PUBLISHED")
    bound_metadata = {
        **dict(record.localization_metadata),
        "source_card_hash": card.content_hash,
        "source_card_revision": card.revision,
    }
    published = replace(
        record,
        translation_status=TranslationStatus.PUBLISHED,
        # Publication creates a new immutable version; the published language
        # version is that new number, not the one it was approved at.
        translation_version=record.translation_version + 1,
        published_language_version=record.translation_version + 1,
        published_at=now,
        localization_metadata=bound_metadata,
    )
    published.validate()
    return published


def retire_translation(
    record: TranslationRecord,
    *,
    reviewer: str,
    now: datetime,
) -> TranslationRecord:
    """Retire a published or approved locale without deleting its history.

    The published language version is retained so an old answer can still point
    at the version that was live; the record simply stops being answerable.
    """

    if not reviewer or not reviewer.strip():
        raise TranslationError("KNOWLEDGE_TRANSLATION_REVIEWER_REQUIRED")
    if record.translation_status not in {
        TranslationStatus.APPROVED,
        TranslationStatus.PUBLISHED,
    }:
        raise TranslationError("KNOWLEDGE_TRANSLATION_NOT_RETIRABLE")
    retired = replace(
        record,
        translation_status=TranslationStatus.RETIRED,
        reviewer=reviewer,
        updated_at=now,
        translation_version=record.translation_version + 1,
    )
    retired.validate()
    return retired


def source_binding_current(card: KnowledgeCard, record: TranslationRecord) -> bool:
    """Whether a published translation still belongs to the current source card.

    Publishing records the source card hash and revision. When the English card
    changes afterwards, the localized text is stale and must not answer until it
    is reviewed and published again. Records published before this binding
    existed carry no hash and keep their historical behaviour.
    """

    bound = record.localization_metadata.get("source_card_hash")
    if not bound:
        return True
    return bound == card.content_hash


def answerable_record(
    store: KnowledgeStore,
    card: KnowledgeCard,
    locale: str,
) -> tuple[TranslationRecord, bool]:
    """Return the record usable for an answer and whether it is a fallback.

    A localized record that is translated but not yet approved, or whose source
    card has changed since publication, is not used as the answer language; the
    caller receives the source record and a ``True`` fallback flag so it can
    state that the translation is not approved.
    """

    resolved = require_locale(locale)
    record = localized_record(store, card, resolved)
    if resolved == DEFAULT_LOCALE or (
        record.approved_for_answer() and source_binding_current(card, record)
    ):
        return record, False
    fallback = source_record(card)
    fallback = replace(
        fallback,
        localization_metadata={
            **dict(fallback.localization_metadata),
            "requested_locale": resolved,
            "requested_translation_status": record.translation_status.value,
            "requested_review_status": record.review_status.value,
            "requested_source_binding_current": source_binding_current(card, record),
        },
    )
    return fallback, True


def localized_card_payload(
    card: KnowledgeCard,
    record: TranslationRecord,
    *,
    source_record_value: TranslationRecord | None = None,
) -> dict[str, object]:
    complete = completeness(record, card_type=card.card_type.value)
    # Any field that must borrow the English source text is reported, so a
    # partially translated card is never presented as fully localized.
    fallback_fields: list[str] = []
    if not record.title:
        fallback_fields.append("title")
    if not record.summary:
        fallback_fields.append("summary")
    if not record.steps:
        fallback_fields.append("steps")
    payload = {
        "card_id": card.card_id,
        "card_type": card.card_type.value,
        "locale": record.locale,
        "language_code": record.language_code,
        "source_language": record.source_language,
        "title": record.title or card.title,
        "summary": record.summary or card.purpose,
        "body": record.body,
        "purpose": record.summary or card.purpose,
        "steps": list(record.steps) if record.steps else list(card.steps),
        "prerequisites": list(record.prerequisites),
        "warnings": list(record.warnings),
        "limitations": list(record.limitations),
        "relations": list(record.relations),
        "technical_glossary": [
            {"term": term, "definition": definition} for term, definition in record.glossary
        ],
        "source_note": record.source_note,
        "translation_status": record.translation_status.value,
        "review_status": record.review_status.value,
        "translation_version": record.translation_version,
        "published_language_version": record.published_language_version,
        "translation_source": record.translation_source.value,
        "machine_translated": record.machine_translated,
        "localization_metadata": dict(record.localization_metadata),
        "complete": complete["complete"],
        "missing_fields": complete["missing_fields"],
        "fallback_fields": tuple(fallback_fields),
        "mixed_language": bool(fallback_fields) and record.locale != FALLBACK_LOCALE,
        "source_url": card.source_url,
        "source_title": card.source_title,
        "source_version": card.source_version,
        "category": card.category,
        "scope": card.scope.value,
        "validation_status": card.validation_status.value,
        "publication_status": card.publication_status.value,
        "reviewer": card.reviewer,
        "published_at": None if card.published_at is None else iso(card.published_at),
        "revision": card.revision,
        "content_hash": card.content_hash,
        "translation_hash": record.content_hash,
    }
    return payload


def detect_content_locale(record: TranslationRecord) -> str:
    """Verify that stored content is actually in its declared locale."""

    return detect_locale(" ".join((record.title, record.summary, record.body)))


def glossary_for(locale: str) -> tuple[tuple[str, str], ...]:
    from .glossary import GLOSSARIES

    return GLOSSARIES.get(canonical_locale(locale, default=FALLBACK_LOCALE), ())


def _string_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise TranslationError("KNOWLEDGE_TRANSLATION_LIST_INVALID")
    return tuple(str(item).strip() for item in value if str(item).strip())


__all__ = [
    "TranslationError",
    "answerable_record",
    "build_translation",
    "completeness",
    "detect_content_locale",
    "glossary_for",
    "localized_card_payload",
    "localized_record",
    "missing_record",
    "publish_translation",
    "review_translation",
    "source_binding_current",
    "source_record",
    "translation_coverage",
]
