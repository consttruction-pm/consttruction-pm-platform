from __future__ import annotations

from datetime import datetime

import pytest

from construction_pm.knowledge.model import KnowledgeError, SearchScope
from construction_pm.knowledge.search import search, tokenize

NOW = "2026-02-01T08:00:00+00:00"
NOW_DT = datetime.fromisoformat(NOW)


def central_scope(user_id: str = "viewer-1") -> SearchScope:
    return SearchScope(
        user_id=user_id,
        tenant_id="tenant-1",
        include_project=False,
        include_user_memory=False,
    )


def _save_published(store, publish_factory, card_factory, **kwargs):
    card = publish_factory(card_factory(**kwargs))
    store.save_card(card)
    return card


def test_relevance_ranking_prefers_title_match(store, card_factory, publish_factory) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Create a Project",
        purpose="Create a project to organize the schedule.",
        topic_key="project.html",
    )
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Create a Resource",
        purpose="Create a resource assignment for a project activity.",
        topic_key="resource.html",
    )
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Calendar Setup",
        purpose="Configure the project calendar.",
        topic_key="calendar.html",
    )

    outcome = search(store, central_scope(), "create project", limit=5)

    assert not outcome.insufficient_knowledge
    assert outcome.hits[0].title == "Create a Project"
    assert all(hit.score >= 1.0 for hit in outcome.hits)
    assert outcome.hits[0].card_id is not None
    assert outcome.hits[0].source_url.startswith("https://docs.oracle.com/")


def test_unknown_question_is_reported_as_insufficient(store, card_factory, publish_factory) -> None:
    _save_published(store, publish_factory, card_factory, title="Create a Project")

    outcome = search(store, central_scope(), "quantum flux capacitor calibrator")

    assert outcome.hits == ()
    assert outcome.insufficient_knowledge is True


def test_drafts_are_excluded_unless_explicitly_requested(store, card_factory) -> None:
    store.save_card(card_factory(title="Draft Secret", topic_key="draft.html"))
    scope = central_scope()

    published_only = search(store, scope, "Draft Secret")
    assert published_only.insufficient_knowledge is True

    with_drafts = search(
        store, scope, "Draft Secret", include_unpublished_central=True
    )
    assert with_drafts.hits[0].title == "Draft Secret"
    assert with_drafts.hits[0].entity_kind == "knowledge_card"


def test_project_knowledge_is_isolated_by_tenant_and_project(store, card_factory, publish_factory) -> None:
    _save_published(
        store, publish_factory, card_factory, title="Central Scheduling", purpose="Schedule projects."
    )
    store.add_project_knowledge(
        tenant_id="tenant-1",
        project_id="PRJ-1",
        title="Site Calendar Notes",
        kind="note",
        content="The site calendar omits Friday.",
        source_ref=None,
        created_by="planner-1",
        occurred_at=NOW,
    )

    inside = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-1", project_id="PRJ-1"),
        "site calendar notes",
    )
    assert any(hit.entity_kind == "project_knowledge" for hit in inside.hits)

    other_tenant = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-2", project_id="PRJ-1"),
        "site calendar notes",
    )
    assert all(hit.entity_kind != "project_knowledge" for hit in other_tenant.hits)

    other_project = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-1", project_id="PRJ-2"),
        "site calendar notes",
    )
    assert all(hit.entity_kind != "project_knowledge" for hit in other_project.hits)


def test_user_memory_is_private_to_its_owner(store) -> None:
    store.save_memory(
        user_id="planner-1",
        tenant_id="tenant-1",
        project_id="PRJ-1",
        memory_key="site_calendar",
        value={"note": "Friday is a non-working day on this site."},
        occurred_at=NOW,
    )

    owner = search(
        store,
        SearchScope(user_id="planner-1", tenant_id="tenant-1", project_id="PRJ-1"),
        "site calendar",
    )
    other_user = search(
        store,
        SearchScope(user_id="planner-2", tenant_id="tenant-1", project_id="PRJ-1"),
        "site calendar",
    )

    assert any(hit.entity_kind == "assistant_memory" for hit in owner.hits)
    assert other_user.hits == ()


def test_persian_normalization_matches_arabic_forms(store, card_factory, publish_factory) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="ایجاد پروژه",
        purpose="برای ایجاد پروژه جدید از منو استفاده کنید.",
        topic_key="fa-project.html",
    )

    outcome = search(store, central_scope(), "ايجاد پروژه")

    assert outcome.insufficient_knowledge is False
    assert outcome.hits[0].title == "ایجاد پروژه"


def test_arabic_orthographic_variants_share_one_token_form() -> None:
    assert tokenize("مستشفى") == tokenize("مستشفي") == ("مستشفی",)
    assert tokenize("إنشاء") == tokenize("انشاء") == ("انشاء",)
    assert tokenize("مَشْـــروع") == ("مشروع",)
    assert tokenize("مشروعاً") == ("مشروعا", "مشروع")


def test_arabic_normalization_does_not_merge_distinct_persian_words() -> None:
    assert tokenize("آب") == ("آب",)
    assert tokenize("اب") == ("اب",)
    assert tokenize("آب") != tokenize("اب")


def test_arabic_hamza_tatweel_and_diacritics_match_the_source_card(
    store, card_factory, publish_factory
) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="إنشاء مشروع",
        purpose="إنشاء مشروع جديد وإضافته إلى هيكل EPS.",
        topic_key="ar-project.html",
    )

    for query in ("انشاء مشروع", "إنشاء مشـــروع", "إِنْشَاء مَشْرُوع"):
        outcome = search(store, central_scope(), query)
        assert outcome.insufficient_knowledge is False, query
        assert outcome.hits[0].title == "إنشاء مشروع", query
        assert outcome.hits[0].evidence["matched_terms"]


def test_arabic_query_and_document_use_the_same_normalization_path(
    store, card_factory, publish_factory
) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="إدارة المستشفى",
        purpose="إدارة المستشفى في المشروع.",
        topic_key="ar-hospital.html",
    )

    plain = search(store, central_scope(), "ادارة المستشفي")
    variant = search(store, central_scope(), "إدارة المستشفى")

    assert plain.hits and variant.hits
    assert plain.hits[0].card_id == variant.hits[0].card_id
    assert plain.hits[0].evidence["matched_terms"] == variant.hits[0].evidence["matched_terms"]


def test_arabic_query_does_not_match_an_unrelated_card(
    store, card_factory, publish_factory
) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="مستشفى",
        purpose="مستشفى ميداني.",
        topic_key="ar-unrelated.html",
    )

    outcome = search(store, central_scope(), "مشروع")

    assert outcome.hits == ()
    assert outcome.insufficient_knowledge is True


def test_tokenizer_drops_stopwords_and_normalizes_digits() -> None:
    assert tokenize("How do I create a project?") == ("create", "project")
    assert tokenize("نسخه ۲۶ از ۳") == ("نسخه", "26")


def test_persian_query_expands_to_official_english_terms(
    store, card_factory, publish_factory
) -> None:
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Create a Project",
        purpose="Create a project and assign it to an EPS node.",
        topic_key="project-fa.html",
    )
    _save_published(
        store,
        publish_factory,
        card_factory,
        title="Schedule a Project",
        purpose="Calculate the project schedule.",
        topic_key="schedule-fa.html",
    )

    outcome = search(store, central_scope(), "چگونه پروژه ایجاد کنم؟", limit=5)

    assert outcome.insufficient_knowledge is False
    assert outcome.hits[0].title == "Create a Project"


def test_persian_query_without_a_real_match_is_still_insufficient(
    store, card_factory, publish_factory
) -> None:
    _save_published(
        store, publish_factory, card_factory, title="Create a Project"
    )

    outcome = search(store, central_scope(), "شارژر کوانتومی")

    assert outcome.hits == ()
    assert outcome.insufficient_knowledge is True


def test_search_contract_validation(store) -> None:
    scope = central_scope()
    with pytest.raises(KnowledgeError):
        search(store, scope, "   ")
    with pytest.raises(KnowledgeError):
        search(store, scope, "project", limit=0)
    with pytest.raises(KnowledgeError):
        SearchScope(user_id="", tenant_id="tenant-1").validate()
    with pytest.raises(KnowledgeError):
        SearchScope(user_id="viewer-1", include_project=True).validate()


# -- multilingual retrieval -------------------------------------------------

MULTILINGUAL_QUERIES = {
    "ru": "Как создать проект?",
    "de": "Wie erstelle ich ein Projekt?",
    "fr": "Comment créer un projet ?",
    "zh-CN": "如何创建项目？",
    "zh-TW": "如何建立專案？",
    "ja": "プロジェクトを作成するには？",
    "ko": "프로젝트를 어떻게 생성합니까?",
    "ar": "كيف أنشئ مشروعاً؟",
}


def _save_card(store, publish_factory, card_factory, **kwargs):
    card = publish_factory(card_factory(**kwargs))
    store.save_card(card)
    return card


def _seed_context(store, publish_factory, card_factory) -> None:
    """Add unrelated published cards so BM25 idf reflects a real corpus.

    With only one or two documents every term is in every document and the
    resulting scores are artificially tiny; these cards keep the multilingual
    ranking tests representative of production retrieval.
    """

    for index, (title, purpose) in enumerate(
        (
            ("Create a Resource", "Create a resource assignment."),
            ("Calendar Setup", "Configure the project calendar."),
            ("Baseline the Schedule", "Save a baseline for comparison."),
            ("Cost Report", "Produce a cost report for the project."),
            ("Assign a Role", "Assign a security role to a user."),
            ("Import an Activity", "Import activities from a spreadsheet."),
            ("Level Resources", "Level resource assignments."),
            ("Publish the Project", "Publish the project plan."),
        )
    ):
        _save_card(
            store,
            publish_factory,
            card_factory,
            title=title,
            purpose=purpose,
            topic_key=f"context-{index}.html",
        )


@pytest.mark.parametrize("locale,query", sorted(MULTILINGUAL_QUERIES.items()))
def test_every_working_language_retrieves_the_official_card(
    store, card_factory, publish_factory, locale: str, query: str
) -> None:
    _seed_context(store, publish_factory, card_factory)
    _save_card(store, publish_factory, card_factory, title="Create a Project", topic_key="p.html")
    _save_card(
        store,
        publish_factory,
        card_factory,
        title="Delete a Project",
        purpose="Remove a project that was created by mistake.",
        topic_key="delete.html",
    )

    outcome = search(store, central_scope(), query, limit=5)

    assert outcome.insufficient_knowledge is False
    assert outcome.hits[0].title == "Create a Project"
    assert outcome.hits[0].language == "en"
    assert outcome.query_locale == locale


def test_chinese_query_without_whitespace_retrieves_the_card(
    store, card_factory, publish_factory
) -> None:
    _save_card(store, publish_factory, card_factory, title="Create a Project", topic_key="p.html")

    outcome = search(store, central_scope(), "创建项目")

    assert outcome.hits[0].title == "Create a Project"
    assert "创建" in outcome.hits[0].matched_terms or "project" in outcome.hits[0].matched_terms


def test_russian_inflected_forms_reach_the_same_stem() -> None:
    assert tokenize("проект") == tokenize("проекта") == tokenize("проектом")
    assert tokenize("создание") == tokenize("создания") == tokenize("созданием")


def test_cjk_tokenization_keeps_technical_terms_without_whitespace() -> None:
    simplified = tokenize("项目创建")
    traditional = tokenize("專案建立")
    japanese = tokenize("プロジェクトを作成するには")
    korean = tokenize("프로젝트를 어떻게 생성합니까")

    assert {"项", "目", "项目", "创建"} <= set(simplified)
    assert {"專", "案", "專案", "建立"} <= set(traditional)
    assert {"プロジェクト", "作成"} <= set(japanese)
    assert {"프로젝트", "생성"} <= set(korean)


def test_locale_filter_returns_the_localized_translation(
    store, card_factory, publish_factory
) -> None:
    from construction_pm.knowledge.model import TranslationSource
    from construction_pm.knowledge.translations import build_translation

    card = _save_card(store, publish_factory, card_factory, title="Create a Project", topic_key="p.html")
    record = build_translation(
        card,
        "ru",
        {
            "title": "Создание проекта",
            "summary": "Создайте проект, чтобы организовать расписание.",
            "body": "Проект объединяет работы и ресурсы.",
            "steps": ["Выберите Проект, затем Создать."],
            "translation_source": TranslationSource.HUMAN.value,
        },
        actor_id="author-1",
        now=NOW_DT,
    )
    store.save_translation(record)

    outcome = search(store, central_scope(), "создать проект", locale="ru")

    assert outcome.response_locale == "ru"
    assert outcome.hits[0].title == "Создание проекта"
    assert outcome.hits[0].language == "ru"
    assert outcome.hits[0].translation_available is True
    assert outcome.hits[0].fallback_used is False
    assert outcome.filters["locale"] == "ru"


def test_locale_without_translation_records_explicit_fallback(
    store, card_factory, publish_factory
) -> None:
    _save_card(store, publish_factory, card_factory, title="Create a Project", topic_key="p.html")

    outcome = search(store, central_scope(), "Wie erstelle ich ein Projekt?", locale="de")

    hit = outcome.hits[0]
    assert hit.language == "en"
    assert hit.fallback_used is True
    assert hit.translation_available is False
    assert hit.translation_status == "missing"
    assert hit.evidence["requested_locale"] == "de"


def test_translation_status_filter_matches_only_requested_state(
    store, card_factory, publish_factory
) -> None:
    from construction_pm.knowledge.model import TranslationSource
    from construction_pm.knowledge.search import SearchFilters
    from construction_pm.knowledge.translations import build_translation

    card = _save_card(store, publish_factory, card_factory, title="Create a Project", topic_key="p.html")
    record = build_translation(
        card,
        "fa",
        {
            "title": "ایجاد پروژه",
            "summary": "برای سازمان‌دهی برنامه یک پروژه ایجاد کنید.",
            "body": "پروژه فعالیت‌ها و منابع را گرد هم می‌آورد.",
            "translation_source": TranslationSource.HUMAN.value,
        },
        actor_id="author-1",
        now=NOW_DT,
    )
    store.save_translation(record)

    translated = search(
        store,
        central_scope(),
        "ایجاد پروژه",
        filters=SearchFilters(locale="fa", translation_status="translated"),
    )
    published = search(
        store,
        central_scope(),
        "ایجاد پروژه",
        filters=SearchFilters(locale="fa", translation_status="published"),
    )
    assert translated.hits
    assert translated.hits[0].translation_status == "translated"
    assert published.hits == ()


def test_hits_carry_retrieval_evidence(store, card_factory, publish_factory) -> None:
    _save_card(store, publish_factory, card_factory, title="Create a Project", topic_key="p.html")

    outcome = search(store, central_scope(), "create project")

    hit = outcome.hits[0]
    assert hit.evidence["query_locale"] == "en"
    assert hit.evidence["content_language"] == "en"
    assert hit.evidence["translation_status"] == "official_source"
    assert hit.matched_fields
    assert hit.matched_terms
    assert outcome.filters == {
        "locale": None,
        "language": None,
        "category": None,
        "source_id": None,
        "source_version": None,
        "card_type": None,
        "translation_status": None,
    }


def test_glossary_terms_are_searchable(store, card_factory, publish_factory) -> None:
    from construction_pm.knowledge.model import TranslationSource
    from construction_pm.knowledge.translations import build_translation

    _seed_context(store, publish_factory, card_factory)
    card = _save_card(store, publish_factory, card_factory, title="Create a Project", topic_key="p.html")
    store.save_translation(
        build_translation(
            card,
            "ru",
            {
                "title": "Создание проекта",
                "summary": "Краткое описание.",
                "body": "Текст.",
                "technical_glossary": [{"term": "Основание", "definition": "Утвержденный план."}],
                "translation_source": TranslationSource.HUMAN.value,
            },
            actor_id="author-1",
            now=NOW_DT,
        )
    )

    outcome = search(store, central_scope(), "основание", locale="ru")
    assert outcome.hits
    assert "glossary" in outcome.hits[0].matched_fields


def test_unsupported_locale_is_rejected(store) -> None:
    with pytest.raises(KnowledgeError):
        search(store, central_scope(), "project", locale="pt-BR")
