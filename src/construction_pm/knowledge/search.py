"""Deterministic, scope-safe multilingual knowledge search for CUBI.

No embeddings, vector service or external model is used. Ranking is lexical
BM25 over normalized multilingual text with source-validity weighting. The
tokenizer is script-aware:

* Persian and Arabic are normalized (letter forms, digits, diacritics),
* Russian tokens are reduced to a common stem so inflected forms match,
* Chinese has no whitespace requirement and is tokenized into characters and
  bigrams,
* Japanese and Korean use their own scripts plus shared Han characters,
* localized engineering terms expand to the English term used by the official
  Version 26 reference, which enables cross-language retrieval.

Results are filtered by the trusted retrieval scope before ranking, so a project
or user record can never appear in another tenant's answer. Every hit carries
retrieval evidence: matched terms, matched fields, content language and the
translation status of the content that was actually searched.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .cards import card_search_text
from .locales import (
    DEFAULT_LOCALE,
    canonical_locale,
    detect_locale,
)
from .translations import source_binding_current
from .model import (
    CardStatus,
    KnowledgeError,
    KnowledgeScope,
    MAX_SEARCH_RESULTS,
    SearchHit,
    SearchOutcome,
    SearchScope,
    TranslationStatus,
    normalize_terms,
)

_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
        "is", "are", "be", "by", "as", "at", "from", "that", "this", "it",
        "how", "what", "when", "where", "which", "do", "does", "can", "i",
        "you", "your", "my", "me", "we", "us", "not", "no", "if", "then",
        "از", "به", "در", "را", "که", "این", "آن", "است", "هست", "با", "برای",
        "و", "یا", "چه", "چگونه", "چطور", "کجا", "کی", "می", "شود", "کنم",
        "کنید", "کن", "من", "ما", "شما", "او", "خود", "بر", "تا", "هم",
        "der", "die", "das", "und", "nicht", "mit", "für", "auf", "ist", "den",
        "dem", "des", "ein", "eine", "einen", "zu", "von", "im", "sich",
        "le", "la", "les", "un", "une", "et", "est", "pour", "avec", "sur",
        "dans", "du", "au", "aux", "ce", "cette",
        "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а",
        "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
        "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от",
        "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже",
        "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был",
        "него", "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там",
        "потом", "себя", "ничего", "ей", "может", "они", "тут", "где", "есть",
        "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам",
        "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет",
        "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой",
        "совсем", "ним", "здесь", "этом", "один", "почти", "мой", "тем",
        "чтобы", "нее", "были", "куда", "зачем", "всех", "никогда", "можно",
        "при", "наконец", "два", "об", "другой", "хоть", "после", "над",
        "больше", "тот", "через", "эти", "нас", "про", "всего", "них",
        "какая", "много", "разве", "три", "эту", "моя", "впрочем", "хорошо",
        "свою", "этой", "перед", "иногда", "лучше", "чуть", "том", "нельзя",
        "такой", "им", "более", "всегда", "конечно", "всю", "между",
    }
)

# CJK ranges. Chinese/Japanese Han characters are tokenized into characters and
# bigrams so a query does not depend on whitespace that the language does not
# use.
_CJK_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2FA1F),
)
_CJK_RUN = re.compile(
    "[" + "".join(f"\\U{start:08x}-\\U{end:08x}" for start, end in _CJK_RANGES) + "]+"
)
_TOKEN = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
_CYRILLIC = re.compile(r"[\u0400-\u04ff]")
_ARABIC_SCRIPT = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
MIN_SCORE = 1.0

# CUBI-owned engineering glossary. It expands a localized query into the English
# terms present in the official sources. It translates no source content and
# cannot introduce a result: ranking still requires a real lexical match.
_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    # Persian
    "پروژه": ("project",),
    "پروژه‌ها": ("project", "projects"),
    "ایجاد": ("create",),
    "ساخت": ("create",),
    "افزودن": ("add",),
    "ویرایش": ("edit",),
    "حذف": ("delete", "remove"),
    "ذخیره": ("save",),
    "فعالیت": ("activity",),
    "فعالیت‌ها": ("activity", "activities"),
    "رابطه": ("relationship", "link"),
    "روابط": ("relationship", "relationships", "link"),
    "زمانبندی": ("schedule", "scheduling"),
    "زمان‌بندی": ("schedule", "scheduling"),
    "زمان": ("schedule", "time"),
    "برنامه": ("schedule", "plan"),
    "تقویم": ("calendar",),
    "منبع": ("resource",),
    "منابع": ("resource", "resources"),
    "هزینه": ("cost", "expense"),
    "هزینه‌ها": ("cost", "costs", "expense"),
    "گزارش": ("report",),
    "گزارش‌ها": ("report", "reports"),
    "کاربر": ("user",),
    "مجوز": ("permission", "access"),
    "تخصیص": ("assign", "assignment"),
    "تقدم": ("predecessor",),
    "جانشین": ("successor",),
    "تاخیر": ("lag",),
    "تأخیر": ("lag",),
    "سطح‌بندی": ("leveling", "level"),
    "وارد": ("import",),
    "خروجی": ("export", "output"),
    "کپی": ("copy",),
    "چاپ": ("print",),
    "خط": ("baseline", "line"),
    "مبنا": ("baseline",),
    # German
    "projekt": ("project",),
    "projekts": ("project", "projects"),
    "projekte": ("project", "projects"),
    "erstellen": ("create",),
    "erstelle": ("create",),
    "erstellt": ("create",),
    "erzeugen": ("create",),
    "erzeuge": ("create",),
    "anlegen": ("create", "new"),
    "aktivität": ("activity",),
    "aktivitäten": ("activity", "activities"),
    "beziehung": ("relationship",),
    "kalender": ("calendar",),
    "ressource": ("resource",),
    "ressourcen": ("resource", "resources"),
    "kosten": ("cost",),
    "bericht": ("report",),
    "terminplan": ("schedule",),
    "vorgänger": ("predecessor",),
    "nachfolger": ("successor",),
    "basisplan": ("baseline",),
    # French
    "projet": ("project",),
    "projets": ("project", "projects"),
    "créer": ("create",),
    "creer": ("create",),
    "crée": ("create",),
    "cree": ("create",),
    "création": ("create", "creation"),
    "creation": ("create", "creation"),
    "créons": ("create",),
    "creons": ("create",),
    "activité": ("activity",),
    "activités": ("activity", "activities"),
    "relation": ("relationship",),
    "calendrier": ("calendar",),
    "ressource": ("resource",),
    "ressources": ("resource", "resources"),
    "coût": ("cost",),
    "cout": ("cost",),
    "rapport": ("report",),
    "échéancier": ("schedule",),
    "echeancier": ("schedule",),
    "prédécesseur": ("predecessor",),
    "successeur": ("successor",),
    "référence": ("baseline", "reference"),
    # Russian (stems after _stem_ru)
    "проект": ("project",),
    "проекты": ("project", "projects"),
    "созда": ("create",),
    "создать": ("create",),
    "активн": ("activity",),
    "связ": ("relationship", "link"),
    "календар": ("calendar",),
    "ресурс": ("resource",),
    "стоим": ("cost",),
    "отчет": ("report",),
    "график": ("schedule",),
    "предшественник": ("predecessor",),
    "последовател": ("successor",),
    "базов": ("baseline",),
    "выравнива": ("leveling", "level"),
    # Simplified Chinese (characters and bigrams emitted by the tokenizer)
    "项目": ("project",),
    "创建": ("create",),
    "新建": ("create", "new"),
    "活动": ("activity",),
    "关系": ("relationship",),
    "日历": ("calendar",),
    "资源": ("resource",),
    "成本": ("cost",),
    "报告": ("report",),
    "进度": ("schedule",),
    "紧前": ("predecessor",),
    "紧后": ("successor",),
    "基准": ("baseline",),
    # Traditional Chinese
    "專案": ("project",),
    "建立": ("create",),
    "活動": ("activity",),
    "關係": ("relationship",),
    "行事曆": ("calendar",),
    "資源": ("resource",),
    "成本": ("cost",),
    "報告": ("report",),
    "進度": ("schedule",),
    "前置": ("predecessor",),
    "後續": ("successor",),
    "基準": ("baseline",),
    # Japanese
    "プロジェクト": ("project",),
    "作成": ("create",),
    "アクティビティ": ("activity",),
    "関係": ("relationship",),
    "カレンダー": ("calendar",),
    "リソース": ("resource",),
    "コスト": ("cost",),
    "レポート": ("report",),
    "スケジュール": ("schedule",),
    "先行": ("predecessor",),
    "後続": ("successor",),
    "基準": ("baseline",),
    # Korean
    "프로젝트": ("project",),
    "생성": ("create",),
    "활동": ("activity",),
    "관계": ("relationship",),
    "달력": ("calendar",),
    "자원": ("resource",),
    "비용": ("cost",),
    "보고서": ("report",),
    "일정": ("schedule",),
    "선행": ("predecessor",),
    "후속": ("successor",),
    "기준": ("baseline",),
    # Arabic
    "مشروع": ("project",),
    "إنشاء": ("create",),
    "أنشئ": ("create",),
    "انشئ": ("create",),
    "أنشي": ("create",),
    "انشي": ("create",),
    "إنش": ("create",),
    "نشاط": ("activity",),
    "علاقة": ("relationship",),
    "تقويم": ("calendar",),
    "مورد": ("resource",),
    "تكلفة": ("cost",),
    "تقرير": ("report",),
    "جدول": ("schedule",),
    "سلف": ("predecessor",),
    "خلف": ("successor",),
    "أساس": ("baseline",),
}

# Arabic orthography normalization. Tashkeel (short vowels) and tanween are
# optional in writing and are removed by ``normalize_terms``; tatweel is also
# stripped there. Alef variants and ta-marbuta are folded here so a query
# matches the same word written differently. Alef-madda (آ) is deliberately not
# folded: in Persian it distinguishes real words such as آب and اب.
_AR_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_AR_FOLD = {
    0x0623: "\u0627",  # أ -> ا
    0x0625: "\u0627",  # إ -> ا
    0x0671: "\u0627",  # ٱ -> ا
    0x0624: "\u0648",  # ؤ -> و
    0x0629: "\u0647",  # ة -> ه
}


def _normalize_arabic(token: str) -> str:
    """Fold Arabic orthographic variants without changing the stored text."""

    if not _ARABIC_SCRIPT.search(token):
        return token
    return _AR_DIACRITICS.sub("", token).translate(_AR_FOLD)


def _canonical_arabic(value: str) -> str:
    """Apply the exact tokenizer path used for queries and documents."""

    return _normalize_arabic(normalize_terms(value))


# Alias keys are indexed in canonical token form so inflected, unvocalized or
# Arabic-typed spellings still expand to the official English term.
_AR_ALIASES = {
    _canonical_arabic(key): value
    for key, value in _QUERY_ALIASES.items()
    if _ARABIC_SCRIPT.search(key)
}

_RU_SUFFIXES = tuple(
    sorted(
        {
            "иями", "ями", "ами", "ого", "ему", "ому", "ыми", "ими", "ость",
            "ности", "ости", "есть", "ть", "ей", "ой", "ый", "ий", "ая",
            "яя", "ое", "ее", "ые", "ую", "юю", "ах", "ях", "ов",
            "ев", "ам", "ям", "ом", "ем", "а", "я", "ы", "и", "о", "е",
            "у", "ю", "ь",
        },
        key=len,
        reverse=True,
    )
)

_JA_PARTICLES = ("を", "は", "が", "に", "で", "と", "へ", "の", "も", "や", "か", "から", "まで", "より")
_KO_PARTICLES = ("에서", "으로", "에게", "께서", "를", "을", "이", "가", "은", "는", "에", "의", "와", "과", "로", "도", "만")
_JA_SUFFIXES = ("するには", "するため", "する", "します", "しました", "したい", "して", "した", "される", "された")
_KO_SUFFIXES = ("합니까", "합니다", "했습니다", "하는", "하려면", "하기", "한다", "한", "할", "해")


@dataclass(frozen=True)
class SearchFilters:
    locale: str | None = None
    language: str | None = None
    category: str | None = None
    source_id: str | None = None
    source_version: str | None = None
    card_type: str | None = None
    translation_status: str | None = None

    def resolved_locale(self) -> str | None:
        if self.locale:
            return canonical_locale(self.locale, default=None) or _raise_locale()
        if self.language:
            if canonical_locale(self.language, default=None):
                return canonical_locale(self.language)
        return None

    def as_dict(self) -> dict[str, object]:
        return {
            "locale": self.locale,
            "language": self.language,
            "category": self.category,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "card_type": self.card_type,
            "translation_status": self.translation_status,
        }


def _raise_locale() -> None:
    raise KnowledgeError("KNOWLEDGE_LOCALE_UNSUPPORTED")


def _contains_cjk(token: str) -> bool:
    return bool(_CJK_RUN.search(token))


def _strip_particles(token: str) -> str:
    value = token
    changed = True
    while changed and len(value) > 2:
        changed = False
        for suffix in _JA_SUFFIXES + _KO_SUFFIXES:
            if value.endswith(suffix) and len(value) - len(suffix) >= 2:
                value = value[: -len(suffix)]
                changed = True
                break
        if changed:
            continue
        for particle in _JA_PARTICLES + _KO_PARTICLES:
            if value.startswith(particle) or value.endswith(particle):
                trimmed = value[len(particle):] if value.startswith(particle) else value[: -len(particle)]
                if len(trimmed) >= 2:
                    value = trimmed
                    changed = True
                    break
    return value


def _cjk_tokens(token: str) -> tuple[str, ...]:
    characters = list(token)
    tokens: list[str] = [character for character in characters]
    for index in range(len(characters) - 1):
        tokens.append(characters[index] + characters[index + 1])
    return tuple(tokens)


def _normalize_cyrillic(token: str) -> str:
    return token.replace("ё", "е").replace("Ё", "Е")


def _arabic_variants(token: str) -> tuple[str, ...]:
    """Return the token plus its accusative form without the final alif.

    Tanween is stripped earlier during query normalization, so an accusative
    such as ``مشروعاً`` arrives as ``مشروعا``. Indexing both spellings keeps the
    inflected query matching the nominative term in a document.
    """

    if not _ARABIC_SCRIPT.search(token):
        return (token,)
    if token.endswith("\u0627") and len(token) >= 5:
        return (token, token[:-1])
    return (token,)


def _stem_ru(token: str) -> str:
    if not _CYRILLIC.search(token):
        return token
    value = _normalize_cyrillic(token.lower())
    for suffix in _RU_SUFFIXES:
        if value.endswith(suffix) and len(value) - len(suffix) >= 4:
            return value[: -len(suffix)]
    return value


def _expand_query(tokens: Sequence[str]) -> tuple[str, ...]:
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        expanded.extend(_QUERY_ALIASES.get(token, ()))
        expanded.extend(_AR_ALIASES.get(token, ()))
        # Russian aliases are keyed by stem; also try the raw spelling.
        if token not in _QUERY_ALIASES and _CYRILLIC.search(token):
            stem = _stem_ru(token)
            expanded.extend(_QUERY_ALIASES.get(stem, ()))
    return tuple(dict.fromkeys(expanded))


def tokenize(value: str) -> tuple[str, ...]:
    normalized = normalize_terms(value)
    tokens: list[str] = []
    for raw in _TOKEN.findall(normalized):
        if _contains_cjk(raw):
            for piece in _CJK_RUN.findall(raw):
                tokens.extend(_cjk_tokens(piece))
            remainder = _CJK_RUN.sub("", raw)
            if remainder:
                token = _stem_ru(_strip_particles(_normalize_arabic(remainder)))
                if len(token) >= 2 and token not in _STOPWORDS:
                    tokens.extend(_arabic_variants(token))
            continue
        token = _stem_ru(_strip_particles(_normalize_arabic(raw)))
        if len(token) >= 2 and token not in _STOPWORDS:
            tokens.extend(_arabic_variants(token))
    return tuple(dict.fromkeys(tokens))


@dataclass(frozen=True)
class _Document:
    entity_kind: str
    entity_id: str
    title: str
    text: str
    scope: KnowledgeScope
    source_url: str | None = None
    card_type: str | None = None
    card_id: str | None = None
    weight: float = 1.0
    language: str | None = None
    source_language: str | None = None
    translation_status: str | None = None
    translation_available: bool = False
    fallback_used: bool = False
    tokens: tuple[str, ...] = ()
    title_tokens: frozenset[str] = frozenset()
    summary_tokens: frozenset[str] = frozenset()
    step_tokens: frozenset[str] = frozenset()
    glossary_tokens: frozenset[str] = frozenset()
    glossary_text: str = ""


def _matches_card_filters(card, filters: SearchFilters) -> bool:
    if filters.category and card.category.lower() != filters.category.lower():
        return False
    if filters.card_type and card.card_type.value != filters.card_type:
        return False
    if filters.source_version and card.source_version != filters.source_version:
        return False
    if filters.source_id and filters.source_id not in card.source_url:
        return False
    return True


def _document_for_card(store, card, filters: SearchFilters) -> _Document:
    requested = filters.resolved_locale()
    if requested and requested != DEFAULT_LOCALE:
        translation = store.get_translation(card.card_id, requested)
        if translation is not None and translation.available():
            if (
                filters.translation_status
                and translation.translation_status.value != filters.translation_status
            ):
                return _Document(
                    entity_kind="knowledge_card",
                    entity_id=card.card_id,
                    title=translation.title or card.title,
                    text="",
                    scope=KnowledgeScope.CENTRAL,
                    source_url=card.source_url,
                    card_type=card.card_type.value,
                    card_id=card.card_id,
                    language=requested,
                    source_language="en",
                    translation_status=translation.translation_status.value,
                    translation_available=True,
                    weight=1.15,
                )
            glossary_text = " ".join(
                f"{term} {definition}" for term, definition in translation.glossary
            )
            text = "\n".join(
                part
                for part in (
                    translation.title,
                    translation.summary,
                    translation.body,
                    "\n".join(translation.steps),
                    "\n".join(translation.prerequisites),
                    "\n".join(translation.warnings),
                    "\n".join(translation.limitations),
                    glossary_text,
                )
                if part
            )
            return _Document(
                entity_kind="knowledge_card",
                entity_id=card.card_id,
                title=translation.title or card.title,
                text=text,
                scope=KnowledgeScope.CENTRAL,
                source_url=card.source_url,
                card_type=card.card_type.value,
                card_id=card.card_id,
                weight=1.2,
                language=requested,
                source_language=translation.source_language,
                translation_status=translation.translation_status.value,
                translation_available=True,
                # The localized text may match the query, but only a reviewed,
                # published translation bound to the current source may answer.
                # An unapproved record is exposed as a fallback so the assistant
                # never presents unreviewed content as a published translation.
                fallback_used=not (
                    translation.approved_for_answer()
                    and source_binding_current(card, translation)
                ),
                glossary_text=glossary_text,
            )
        return _Document(
            entity_kind="knowledge_card",
            entity_id=card.card_id,
            title=card.title,
            text=card_search_text(card),
            scope=KnowledgeScope.CENTRAL,
            source_url=card.source_url,
            card_type=card.card_type.value,
            card_id=card.card_id,
            weight=1.1,
            language=DEFAULT_LOCALE,
            source_language=DEFAULT_LOCALE,
            translation_status=(
                translation.translation_status.value
                if translation is not None
                else TranslationStatus.MISSING.value
            ),
            translation_available=False,
            fallback_used=True,
        )
    if filters.translation_status and filters.translation_status != "official_source":
        # Without a requested non-source locale the searchable content is the
        # official English source, whose status is "official_source". Filtering
        # for a translation status therefore yields no match rather than
        # silently searching content in a different language.
        return _empty_document(card)
    return _Document(
        entity_kind="knowledge_card",
        entity_id=card.card_id,
        title=card.title,
        text=card_search_text(card),
        scope=KnowledgeScope.CENTRAL,
        source_url=card.source_url,
        card_type=card.card_type.value,
        card_id=card.card_id,
        weight=1.15,
        language=DEFAULT_LOCALE,
        source_language=DEFAULT_LOCALE,
        translation_status="official_source",
        translation_available=True,
        fallback_used=False,
    )


def _empty_document(card) -> _Document:
    return _Document(
        entity_kind="knowledge_card",
        entity_id=card.card_id,
        title=card.title,
        text="",
        scope=KnowledgeScope.CENTRAL,
        source_url=card.source_url,
        card_type=card.card_type.value,
        card_id=card.card_id,
        language=DEFAULT_LOCALE,
        translation_status=TranslationStatus.MISSING.value,
    )


def _documents(
    store,
    scope: SearchScope,
    *,
    include_unpublished_central: bool,
    filters: SearchFilters | None = None,
) -> tuple[_Document, ...]:
    filters = filters or SearchFilters()
    documents: list[_Document] = []
    if scope.include_central:
        statuses = (
            [CardStatus.DRAFT.value, CardStatus.VALIDATED.value, CardStatus.PUBLISHED.value]
            if include_unpublished_central
            else [CardStatus.PUBLISHED.value]
        )
        for card in store.list_cards(scope="central", publication_statuses=statuses):
            if not _matches_card_filters(card, filters):
                continue
            document = _document_for_card(store, card, filters)
            if not document.text:
                continue
            documents.append(document)
    if scope.include_project and scope.tenant_id and scope.project_id:
        for entry in store.list_project_knowledge(scope.tenant_id, scope.project_id):
            if str(entry.get("status")) != "active":
                continue
            documents.append(
                _Document(
                    entity_kind="project_knowledge",
                    entity_id=str(entry["knowledge_id"]),
                    title=str(entry["title"]),
                    text=f"{entry['title']}\n{entry['kind']}\n{entry['content']}",
                    scope=KnowledgeScope.PROJECT,
                    weight=1.0,
                    language=detect_locale(f"{entry['title']} {entry['content']}"),
                )
            )
    if scope.include_user_memory and scope.tenant_id and scope.project_id:
        for entry in store.list_memory(
            user_id=scope.user_id,
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
        ):
            value = entry.get("value")
            rendered = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            documents.append(
                _Document(
                    entity_kind="assistant_memory",
                    entity_id=str(entry["memory_id"]),
                    title=str(entry["memory_key"]).replace("_", " "),
                    text=f"{entry['memory_key']}\n{rendered}",
                    scope=KnowledgeScope.USER_MEMORY,
                    weight=0.7,
                    language=detect_locale(str(entry["memory_key"])),
                )
            )
    result: list[_Document] = []
    for document in documents:
        tokens = _document_tokens(document.text)
        if not tokens:
            continue
        result.append(
            _Document(
                **{
                    **document.__dict__,
                    "tokens": tokens,
                    "title_tokens": frozenset(_document_tokens(document.title)),
                    "summary_tokens": frozenset(
                        _document_tokens(
                            document.text.split("\n")[1] if "\n" in document.text else ""
                        )
                    ),
                    "step_tokens": frozenset(tokens),
                    "glossary_tokens": frozenset(
                        _document_tokens(document.glossary_text)
                    ),
                }
            )
        )
    return tuple(result)


def _document_tokens(value: str) -> tuple[str, ...]:
    """Index a document with its own terms plus their canonical English terms.

    The alias table maps localized engineering vocabulary to the English term
    used by the official reference. Applying it at index time and at query time
    makes retrieval work in both directions: a Russian question finds an
    English card, and an English question finds an approved Russian translation.
    """

    return _expand_query(tokenize(value))


def _snippet(text: str, query_tokens: Sequence[str], *, limit: int = 260) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    lowered = compact.lower()
    best_index = -1
    for token in query_tokens:
        index = lowered.find(token)
        if index >= 0 and (best_index < 0 or index < best_index):
            best_index = index
    start = 0 if best_index < 0 else max(0, best_index - limit // 3)
    fragment = compact[start:start + limit]
    if start > 0:
        fragment = "..." + fragment
    if start + limit < len(compact):
        fragment = fragment + "..."
    return fragment


def _matched_fields(document: _Document, query_tokens: Sequence[str]) -> tuple[str, ...]:
    tokens = set(query_tokens)
    fields: list[str] = []
    if tokens & document.title_tokens:
        fields.append("title")
    if tokens & document.summary_tokens:
        fields.append("summary")
    if tokens & document.step_tokens:
        fields.append("steps")
    if tokens & document.glossary_tokens:
        fields.append("glossary")
    if not fields and tokens & set(document.tokens):
        fields.append("body")
    return tuple(fields)


def search(
    store,
    scope: SearchScope,
    query: str,
    *,
    limit: int = 10,
    min_score: float = MIN_SCORE,
    include_unpublished_central: bool = False,
    locale: str | None = None,
    filters: SearchFilters | Mapping[str, object] | None = None,
) -> SearchOutcome:
    scope.validate()
    if not isinstance(query, str) or not query.strip():
        raise KnowledgeError("KNOWLEDGE_SEARCH_QUERY_REQUIRED")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise KnowledgeError("KNOWLEDGE_SEARCH_LIMIT_INVALID")
    if filters is None:
        resolved_filters = SearchFilters(locale=locale)
    elif isinstance(filters, SearchFilters):
        resolved_filters = filters if locale is None else SearchFilters(
            locale=locale,
            language=filters.language,
            category=filters.category,
            source_id=filters.source_id,
            source_version=filters.source_version,
            card_type=filters.card_type,
            translation_status=filters.translation_status,
        )
    else:
        resolved_filters = SearchFilters(
            locale=locale or filters.get("locale"),
            language=filters.get("language"),
            category=filters.get("category"),
            source_id=filters.get("source_id"),
            source_version=filters.get("source_version"),
            card_type=filters.get("card_type"),
            translation_status=filters.get("translation_status"),
        )
    response_locale = resolved_filters.resolved_locale() or (
        canonical_locale(locale, default=None) if locale else None
    )
    query_locale = detect_locale(query)
    query_tokens = _expand_query(tokenize(query))
    if not query_tokens:
        return SearchOutcome(
            query=query.strip(),
            hits=(),
            insufficient_knowledge=True,
            query_locale=query_locale,
            response_locale=response_locale or query_locale,
            filters=resolved_filters.as_dict(),
        )
    documents = _documents(
        store,
        scope,
        include_unpublished_central=include_unpublished_central,
        filters=resolved_filters,
    )
    if not documents:
        return SearchOutcome(
            query=query.strip(),
            hits=(),
            insufficient_knowledge=True,
            query_locale=query_locale,
            response_locale=response_locale or query_locale,
            filters=resolved_filters.as_dict(),
        )

    document_frequency: dict[str, int] = {}
    for document in documents:
        for token in set(document.tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1
    average_length = sum(len(document.tokens) for document in documents) / len(documents) or 1.0
    k1 = 1.2
    b = 0.75
    scored: list[SearchHit] = []
    for document in documents:
        term_frequency: dict[str, int] = {}
        for token in document.tokens:
            term_frequency[token] = term_frequency.get(token, 0) + 1
        score = 0.0
        matched: list[str] = []
        for token in set(query_tokens):
            frequency = term_frequency.get(token, 0)
            if not frequency:
                continue
            matched.append(token)
            df = document_frequency.get(token, 0)
            idf = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (
                1 - b + b * len(document.tokens) / average_length
            )
            score += idf * (frequency * (k1 + 1)) / denominator
        if score <= 0:
            continue
        # The title bonus is measured against the terms that actually matched,
        # not every token in the query. A cross-language query contributes
        # untranslatable words (particles, question words) that must not dilute
        # the ranking of a fully matching localized query.
        matched_unique = set(matched)
        if matched_unique:
            title_matches = sum(
                1 for token in matched_unique if token in document.title_tokens
            )
            score += 1.5 * (title_matches / len(matched_unique))
            if title_matches == len(matched_unique) and len(matched_unique) >= 2:
                score += 1.0
        score *= document.weight
        scored.append(
            SearchHit(
                entity_kind=document.entity_kind,
                entity_id=document.entity_id,
                title=document.title,
                snippet=_snippet(document.text, query_tokens),
                score=round(score, 6),
                scope=document.scope,
                source_url=document.source_url,
                card_type=document.card_type,
                card_id=document.card_id,
                language=document.language,
                source_language=document.source_language,
                translation_status=document.translation_status,
                translation_available=document.translation_available,
                fallback_used=document.fallback_used,
                matched_terms=tuple(sorted(matched)),
                matched_fields=_matched_fields(document, query_tokens),
                evidence={
                    "query_locale": query_locale,
                    "requested_locale": resolved_filters.resolved_locale(),
                    "content_language": document.language,
                    "source_language": document.source_language,
                    "translation_status": document.translation_status,
                    "translation_available": document.translation_available,
                    "fallback_used": document.fallback_used,
                    "matched_terms": sorted(matched),
                    "filters": resolved_filters.as_dict(),
                },
            )
        )
    scored.sort(key=lambda hit: (-hit.score, hit.title, hit.entity_id))
    hits = tuple(hit for hit in scored[:limit] if hit.score >= min_score)
    return SearchOutcome(
        query=query.strip(),
        hits=hits,
        insufficient_knowledge=not hits,
        query_locale=query_locale,
        response_locale=response_locale or query_locale,
        filters=resolved_filters.as_dict(),
    )


def answer_terms(question: str) -> tuple[str, ...]:
    return tokenize(question)


__all__ = [
    "MIN_SCORE",
    "SearchFilters",
    "answer_terms",
    "search",
    "tokenize",
]
