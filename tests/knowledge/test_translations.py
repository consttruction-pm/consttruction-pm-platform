from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from construction_pm.knowledge.locales import SUPPORTED_LOCALES
from construction_pm.knowledge.model import (
    KnowledgeError,
    ReviewStatus,
    TranslationSource,
    TranslationStatus,
)
from construction_pm.knowledge.translations import (
    TranslationError,
    answerable_record,
    build_translation,
    completeness,
    localized_card_payload,
    localized_record,
    missing_record,
    publish_translation,
    retire_translation,
    review_translation,
    source_record,
    translation_coverage,
)

NOW = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

PAYLOADS = {
    "ru": {
        "title": "Создание проекта",
        "summary": "Создайте проект, чтобы организовать расписание.",
        "body": "Проект объединяет работы, ресурсы и календарь.",
        "steps": ("Выберите «Проект», затем «Создать».",),
        "technical_glossary": [{"term": "Проект", "definition": "Контейнер работ."}],
        "source_note": "Официальный источник версии 26.",
    },
    "fa": {
        "title": "ایجاد پروژه",
        "summary": "برای سازمان‌دهی برنامه یک پروژه ایجاد کنید.",
        "body": "پروژه فعالیت‌ها، منابع و تقویم را گرد هم می‌آورد.",
        "steps": ("گزینه پروژه و سپس ایجاد را انتخاب کنید.",),
        "source_note": "منبع رسمی نسخه ۲۶.",
    },
    "de": {
        "title": "Projekt erstellen",
        "summary": "Erstellen Sie ein Projekt, um den Terminplan zu organisieren.",
        "body": "Ein Projekt bündelt Vorgänge, Ressourcen und Kalender.",
        "steps": ("Wählen Sie Projekt und dann Erstellen.",),
    },
    "ja": {
        "title": "プロジェクトの作成",
        "summary": "スケジュールを整理するためにプロジェクトを作成します。",
        "body": "プロジェクトはアクティビティ、リソース、カレンダーをまとめます。",
        "steps": ("プロジェクトを選択し、作成をクリックします。",),
    },
}


def _build(card, locale: str, *, payload=None, now=NOW, existing=None, source=TranslationSource.HUMAN):
    body = dict(PAYLOADS.get(locale, PAYLOADS["ru"] if locale != "fa" else PAYLOADS["fa"]))
    if payload:
        body.update(payload)
    body.setdefault("translation_source", source.value)
    return build_translation(
        card, locale, body, actor_id="author-1", now=now, existing=existing
    )


def test_published_source_card_is_represented_as_source_record(card_factory, publish_factory) -> None:
    card = publish_factory(card_factory())
    record = source_record(card)
    assert record.locale == "en"
    assert record.translation_status is TranslationStatus.PUBLISHED
    assert record.review_status is ReviewStatus.APPROVED
    assert record.published_language_version == record.translation_version
    assert record.translation_source is TranslationSource.OFFICIAL_SOURCE
    assert record.approved_for_answer()


def test_unpublished_source_card_is_never_reported_as_published(card_factory) -> None:
    record = source_record(card_factory())
    assert record.translation_status is TranslationStatus.DRAFT
    assert record.review_status is ReviewStatus.PENDING
    assert record.published_language_version is None
    assert not record.approved_for_answer()


def test_every_locale_is_missing_until_a_record_exists(store, card_factory) -> None:
    card = card_factory()
    for locale in SUPPORTED_LOCALES:
        record = localized_record(store, card, locale)
        if locale == "en":
            assert record.available()
        else:
            assert record.translation_status is TranslationStatus.MISSING
            assert record.locale == locale


def test_saving_one_locale_does_not_touch_another(store, card_factory) -> None:
    card = card_factory()
    russian = _build(card, "ru")
    store.save_translation(russian)
    assert store.get_translation(card.card_id, "fa") is None
    assert localized_record(store, card, "fa").translation_status is TranslationStatus.MISSING
    assert localized_record(store, card, "ru").title == "Создание проекта"


def test_translation_starts_translated_and_pending_review(store, card_factory) -> None:
    record = _build(card_factory(), "ru")
    assert record.translation_status is TranslationStatus.TRANSLATED
    assert record.review_status is ReviewStatus.PENDING
    assert record.translation_version == 1
    assert len(record.content_hash) == 64


def test_review_and_publish_are_per_locale(store, card_factory, publish_factory) -> None:
    card = publish_factory(card_factory())
    russian = _build(card, "ru")
    persian = _build(card, "fa")
    store.save_translation(russian)
    store.save_translation(persian)

    approved_ru = review_translation(russian, reviewer="reviewer-1", accept=True, now=NOW)
    store.save_translation(approved_ru)
    published_ru = publish_translation(card, approved_ru, reviewer="reviewer-1", now=LATER)
    store.save_translation(published_ru)

    stored_fa = store.get_translation(card.card_id, "fa")
    assert stored_fa.translation_status is TranslationStatus.TRANSLATED
    assert stored_fa.published_language_version is None
    assert store.get_translation(card.card_id, "ru").translation_status is TranslationStatus.PUBLISHED
    # Version 1 is the content, 2 the approval, 3 the publication itself.
    assert store.get_translation(card.card_id, "ru").published_language_version == 3


def test_retired_locale_keeps_its_version_and_stops_answering(
    store, card_factory, publish_factory
) -> None:
    card = publish_factory(card_factory())
    russian = _build(card, "ru")
    approved = review_translation(russian, reviewer="reviewer-1", accept=True, now=NOW)
    published = publish_translation(card, approved, reviewer="reviewer-1", now=LATER)
    retired = retire_translation(published, reviewer="retirer-1", now=LATER)

    assert retired.translation_status is TranslationStatus.RETIRED
    assert retired.published_language_version == 3
    assert retired.available() is False
    assert retired.approved_for_answer() is False
    store.save_translation(retired)

    record, fallback = answerable_record(store, card, "ru")
    assert fallback is True
    assert record.locale == "en"
    assert record.localization_metadata["requested_translation_status"] == "retired"

    with pytest.raises(TranslationError):
        retire_translation(_build(card, "fa"), reviewer="retirer-1", now=LATER)


def test_machine_translation_cannot_be_approved_or_published(card_factory, publish_factory) -> None:
    card = publish_factory(card_factory())
    machine = _build(card, "de", source=TranslationSource.MACHINE)
    assert machine.machine_translated is True
    with pytest.raises(TranslationError):
        review_translation(machine, reviewer="reviewer-1", accept=True, now=NOW)
    with pytest.raises(TranslationError):
        publish_translation(card, machine, reviewer="reviewer-1", now=NOW)


def test_translation_cannot_be_published_before_source_card(card_factory) -> None:
    card = card_factory()
    record = review_translation(_build(card, "fa"), reviewer="reviewer-1", accept=True, now=NOW)
    with pytest.raises(TranslationError):
        publish_translation(card, record, reviewer="reviewer-1", now=NOW)


def test_translation_cannot_be_published_without_approval(card_factory, publish_factory) -> None:
    card = publish_factory(card_factory())
    with pytest.raises(TranslationError):
        publish_translation(card, _build(card, "ru"), reviewer="reviewer-1", now=NOW)


def test_rejection_returns_to_review_required(card_factory) -> None:
    record = _build(card_factory(), "ja")
    rejected = review_translation(record, reviewer="reviewer-1", accept=False, now=NOW)
    assert rejected.translation_status is TranslationStatus.REVIEW_REQUIRED
    assert rejected.review_status is ReviewStatus.REJECTED
    assert rejected.reviewer == "reviewer-1"
    assert rejected.reviewed_at is None


def test_unapproved_translation_falls_back_to_source_with_metadata(store, card_factory) -> None:
    card = card_factory()
    store.save_translation(_build(card, "ru"))
    record, fallback = answerable_record(store, card, "ru")
    assert fallback is True
    assert record.locale == "en"
    assert record.localization_metadata["requested_locale"] == "ru"
    assert record.localization_metadata["requested_translation_status"] == "translated"


def test_approved_translation_is_answerable(store, card_factory, publish_factory) -> None:
    card = publish_factory(card_factory())
    approved = review_translation(_build(card, "ru"), reviewer="reviewer-1", accept=True, now=NOW)
    store.save_translation(approved)
    record, fallback = answerable_record(store, card, "ru")
    assert fallback is False
    assert record.locale == "ru"
    assert record.approved_for_answer()


def test_missing_translation_falls_back_with_missing_status(store, card_factory) -> None:
    card = card_factory()
    record, fallback = answerable_record(store, card, "ko")
    assert fallback is True
    assert record.localization_metadata["requested_translation_status"] == "missing"


def test_editing_bumps_version_and_resets_review(store, card_factory) -> None:
    card = card_factory()
    first = _build(card, "ru")
    approved = review_translation(first, reviewer="reviewer-1", accept=True, now=NOW)
    store.save_translation(approved)
    second = _build(card, "ru", payload={"summary": "Обновленное описание."}, now=LATER, existing=approved)
    # 1 content, 2 approval, 3 the edit that supersedes the approval.
    assert second.translation_version == 3
    assert second.translation_status is TranslationStatus.TRANSLATED
    assert second.review_status is ReviewStatus.PENDING
    assert second.published_language_version is None
    assert second.content_hash != approved.content_hash


def test_content_hash_changes_only_with_content(card_factory) -> None:
    card = card_factory()
    first = _build(card, "ru")
    same = _build(card, "ru")
    changed = _build(card, "ru", payload={"title": "Другое название"})
    assert first.content_hash == same.content_hash
    assert changed.content_hash != first.content_hash


def test_completeness_reports_missing_operation_steps(card_factory) -> None:
    record = _build(card_factory(), "ru", payload={"steps": ()})
    result = completeness(record, card_type="operation")
    assert result["complete"] is False
    assert "steps" in result["missing_fields"]
    missing = missing_record("card-1", "ar", updated_at=NOW)
    assert completeness(missing)["missing_fields"] == ["title", "summary", "body"]


def test_source_locale_translation_is_rejected_by_the_contract(card_factory) -> None:
    record = _build(card_factory(), "ru")
    with pytest.raises(KnowledgeError):
        replace(record, locale="en", language_code="ru").validate()
    with pytest.raises(KnowledgeError):
        replace(record, locale="pt-BR").validate()


def test_published_record_requires_real_review_metadata(card_factory, publish_factory) -> None:
    card = publish_factory(card_factory())
    approved = review_translation(_build(card, "ru"), reviewer="reviewer-1", accept=True, now=NOW)
    published = publish_translation(card, approved, reviewer="reviewer-1", now=LATER)
    assert published.reviewed_at is not None
    assert published.published_at is not None
    with pytest.raises(KnowledgeError):
        replace(published, published_at=None).validate()
    with pytest.raises(KnowledgeError):
        replace(published, published_language_version=None).validate()


def test_coverage_counts_each_locale_independently(store, card_factory, publish_factory) -> None:
    first = publish_factory(card_factory(topic_key="a.html"))
    second = publish_factory(card_factory(topic_key="b.html", title="Create a Resource"))
    store.save_card(first)
    store.save_card(second)
    store.save_translation(_build(first, "ru"))
    approved = review_translation(_build(second, "ru"), reviewer="reviewer-1", accept=True, now=NOW)
    store.save_translation(publish_translation(second, approved, reviewer="reviewer-1", now=LATER))

    coverage = translation_coverage(store, [first.card_id, second.card_id])
    assert coverage["cards"] == 2
    assert coverage["locales"]["ru"]["translated"] == 1
    assert coverage["locales"]["ru"]["published"] == 1
    assert coverage["locales"]["fa"]["missing"] == 0  # a missing record is not stored
    assert coverage["locales"]["fa"]["translated"] == 0


def test_coverage_reports_slots_and_answerable_per_locale(
    store, card_factory, publish_factory
) -> None:
    """Coverage must use the whole card set as the denominator.

    Regression: the previous report counted only stored records, so one
    translated card looked like full locale coverage and a translated-but-
    unpublished locale looked usable.
    """

    published = publish_factory(card_factory(topic_key="a.html"))
    draft = card_factory(topic_key="b.html", title="Create a Resource")
    store.save_card(published)
    store.save_card(draft)
    approved = review_translation(
        _build(published, "ru"), reviewer="reviewer-1", accept=True, now=NOW
    )
    store.save_translation(publish_translation(published, approved, reviewer="reviewer-1", now=LATER))
    store.save_translation(_build(draft, "ru"))

    coverage = translation_coverage(store, [published.card_id, draft.card_id])
    slots = 2 * 9
    assert coverage["available_slots"] == slots
    assert coverage["filled_slots"] == 2
    assert coverage["published_slots"] == 1
    assert coverage["missing_slots"] == slots - 2
    assert coverage["coverage_percent"] == round(2 * 100.0 / slots, 2)
    inventory = coverage["inventory"]
    assert inventory["ru"]["records"] == 2
    assert inventory["ru"]["published"] == 1
    assert inventory["ru"]["answerable"] == 1
    assert inventory["ru"]["missing_slots"] == 0
    assert inventory["fa"]["missing_slots"] == 2
    assert inventory["fa"]["answerable"] == 0


def test_coverage_does_not_count_a_stale_translation_as_answerable(
    store, card_factory, publish_factory
) -> None:
    card = publish_factory(card_factory(topic_key="a.html"))
    store.save_card(card)
    approved = review_translation(_build(card, "ru"), reviewer="reviewer-1", accept=True, now=NOW)
    store.save_translation(publish_translation(card, approved, reviewer="reviewer-1", now=LATER))
    changed = replace(card, revision=card.revision + 1, content_hash="f" * 64)
    store.save_card(changed, expected_version=card.revision)

    coverage = translation_coverage(store, [changed])
    assert coverage["inventory"]["ru"]["published"] == 1
    assert coverage["inventory"]["ru"]["answerable"] == 0
    assert coverage["inventory"]["ru"]["stale_source_binding"] == 1


def test_localized_payload_marks_fields_borrowed_from_english(card_factory) -> None:
    card = card_factory()
    partial = _build(card, "ru", payload={"steps": ()})
    payload = localized_card_payload(card, partial)
    assert payload["mixed_language"] is True
    assert "steps" in payload["fallback_fields"]
    assert payload["missing_fields"] == ["steps"]
    full = localized_card_payload(card, _build(card, "ru"))
    assert full["mixed_language"] is False
    assert full["fallback_fields"] == ()
