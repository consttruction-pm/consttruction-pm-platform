"""Deterministic, scope-safe knowledge search for the CUBI assistant.

No embeddings, vector service or external model is used. Ranking is lexical
BM25 over normalized multilingual text with source-validity weighting. Results
are filtered by the trusted retrieval scope before ranking, so a project or user
record can never appear in another tenant's answer.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Sequence

from .cards import card_search_text
from .model import (
    CardStatus,
    KnowledgeError,
    KnowledgeScope,
    MAX_SEARCH_RESULTS,
    SearchHit,
    SearchOutcome,
    SearchScope,
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
    }
)
_TOKEN = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
MIN_SCORE = 1.0

# CUBI-owned engineering glossary used only to expand a Persian query into the
# English terms present in the official Version 26 sources. It translates no
# source content and cannot introduce a result: ranking still requires a real
# lexical match in a stored record.
_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
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
}


def _expand_query(tokens: Sequence[str]) -> tuple[str, ...]:
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        expanded.extend(_QUERY_ALIASES.get(token, ()))
    return tuple(dict.fromkeys(expanded))


def tokenize(value: str) -> tuple[str, ...]:
    normalized = normalize_terms(value)
    tokens = [
        token
        for token in _TOKEN.findall(normalized)
        if len(token) >= 2 and token not in _STOPWORDS
    ]
    return tuple(tokens)


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
    tokens: tuple[str, ...] = ()
    title_tokens: frozenset[str] = frozenset()


def _documents(
    store,
    scope: SearchScope,
    *,
    include_unpublished_central: bool,
) -> tuple[_Document, ...]:
    documents: list[_Document] = []
    if scope.include_central:
        statuses = (
            [CardStatus.DRAFT.value, CardStatus.VALIDATED.value, CardStatus.PUBLISHED.value]
            if include_unpublished_central
            else [CardStatus.PUBLISHED.value]
        )
        for card in store.list_cards(scope="central", publication_statuses=statuses):
            documents.append(
                _Document(
                    entity_kind="knowledge_card",
                    entity_id=card.card_id,
                    title=card.title,
                    text=card_search_text(card),
                    scope=KnowledgeScope.CENTRAL,
                    source_url=card.source_url,
                    card_type=card.card_type.value,
                    card_id=card.card_id,
                    weight=1.15,
                )
            )
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
                )
            )
    return tuple(
        _Document(
            **{
                **document.__dict__,
                "tokens": tokenize(document.text),
                "title_tokens": frozenset(tokenize(document.title)),
            }
        )
        if not document.tokens
        else document
        for document in documents
    )


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


def search(
    store,
    scope: SearchScope,
    query: str,
    *,
    limit: int = 10,
    min_score: float = MIN_SCORE,
    include_unpublished_central: bool = False,
) -> SearchOutcome:
    scope.validate()
    if not isinstance(query, str) or not query.strip():
        raise KnowledgeError("KNOWLEDGE_SEARCH_QUERY_REQUIRED")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_SEARCH_RESULTS:
        raise KnowledgeError("KNOWLEDGE_SEARCH_LIMIT_INVALID")
    query_tokens = _expand_query(tokenize(query))
    if not query_tokens:
        return SearchOutcome(query=query.strip(), hits=(), insufficient_knowledge=True)
    documents = _documents(
        store, scope, include_unpublished_central=include_unpublished_central
    )
    if not documents:
        return SearchOutcome(query=query.strip(), hits=(), insufficient_knowledge=True)

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
        for token in set(query_tokens):
            frequency = term_frequency.get(token, 0)
            if not frequency:
                continue
            df = document_frequency.get(token, 0)
            idf = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (
                1 - b + b * len(document.tokens) / average_length
            )
            score += idf * (frequency * (k1 + 1)) / denominator
        if score <= 0:
            continue
        title_matches = sum(1 for token in query_tokens if token in document.title_tokens)
        score += 1.5 * (title_matches / len(set(query_tokens)))
        if all(token in document.title_tokens for token in set(query_tokens)):
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
            )
        )
    scored.sort(key=lambda hit: (-hit.score, hit.title, hit.entity_id))
    hits = tuple(
        hit for hit in scored[:limit] if hit.score >= min_score
    )
    return SearchOutcome(
        query=query.strip(),
        hits=hits,
        insufficient_knowledge=not hits,
    )


def answer_terms(question: str) -> tuple[str, ...]:
    return tokenize(question)


__all__ = ["MIN_SCORE", "answer_terms", "search", "tokenize"]
