#!/usr/bin/env python3
"""Build multilingual evidence for the CUBI knowledge assistant.

The command is read-only against the supplied evidence database except for the
translation seed. Destructive publication is performed on a copy, so the
evidence database itself keeps every official card as an unreviewed draft.

Usage::

    python tools/knowledge_multilingual_evidence.py \
        --db docs/workspace/evidence/.../cubi-knowledge-v26.sqlite3 \
        --out docs/workspace/evidence/... \
        --copy-db /tmp/cubi-multilingual-smoke.sqlite3
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from construction_pm.application.authorization import default_project_policy  # noqa: E402
from construction_pm.knowledge.assistant import (  # noqa: E402
    AssistantPrincipal,
    KnowledgeAssistant,
)
from construction_pm.knowledge.cards import publish_card, review_card  # noqa: E402
from construction_pm.knowledge.locales import (  # noqa: E402
    SUPPORTED_LOCALES,
    locale_registry,
)
from construction_pm.knowledge.model import SearchScope  # noqa: E402
from construction_pm.knowledge.search import search  # noqa: E402
from construction_pm.knowledge.sqlite_store import SqliteKnowledgeStore  # noqa: E402
from construction_pm.knowledge.translation_seed import seed_translations  # noqa: E402
from construction_pm.knowledge.translations import (  # noqa: E402
    localized_record,
    publish_translation,
    review_translation,
)
from construction_pm.knowledge.workflow import ProjectCreationWorkflow  # noqa: E402

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
FLAGSHIP_TITLE = "Create a project"
QUESTIONS = {
    "fa": "چگونه یک پروژه ایجاد کنم؟",
    "en": "How do I create a project?",
    "de": "Wie erstelle ich ein Projekt?",
    "zh-CN": "如何创建项目？",
    "zh-TW": "如何建立專案？",
    "ar": "كيف أنشئ مشروعاً؟",
    "fr": "Comment créer un projet ?",
    "ja": "プロジェクトを作成するには？",
    "ko": "프로젝트를 어떻게 생성합니까?",
    "ru": "Как создать проект?",
}


class NullGateway:
    def list_projects(self):  # pragma: no cover - not exercised
        return ()

    def get_project(self, project_id):  # pragma: no cover
        return None

    def create_project(self, **kwargs):  # pragma: no cover
        raise AssertionError("evidence script must not create projects")

    def update_project(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("evidence script must not update projects")


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _flagship(store: SqliteKnowledgeStore):
    wanted = FLAGSHIP_TITLE.casefold()
    for card in store.list_cards(scope="central"):
        if card.title.casefold() == wanted:
            return card
    raise SystemExit(f"flagship card not found: {FLAGSHIP_TITLE!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--copy-db", required=True)
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    seed_store = SqliteKnowledgeStore(args.db)
    try:
        seed = seed_translations(seed_store, now=NOW)
    finally:
        seed_store.close()
    store = SqliteKnowledgeStore(args.db)
    try:
        card = _flagship(store)
        rows = []
        for locale in SUPPORTED_LOCALES:
            record = localized_record(store, card, locale)
            rows.append(
                {
                    "locale": locale,
                    "language_code": record.language_code,
                    "translation_status": record.translation_status.value,
                    "review_status": record.review_status.value,
                    "translation_version": record.translation_version,
                    "published_language_version": record.published_language_version,
                    "machine_translated": record.machine_translated,
                    "title": record.title,
                    "steps": len(record.steps),
                    "glossary_terms": len(record.glossary),
                    "content_hash": record.content_hash,
                }
            )
        _write(
            out / "translation-matrix.json",
            {
                "contract": "cubi-knowledge-translation-matrix.v1",
                "card_id": card.card_id,
                "card_title": card.title,
                "seed_written": seed,
                "locales": rows,
            },
        )
    finally:
        store.close()

    shutil.copyfile(args.db, args.copy_db)
    smoke = SqliteKnowledgeStore(args.copy_db)
    try:
        card = _flagship(smoke)
        reviewed = review_card(card, reviewer="evidence-reviewer", accept=True)
        published = publish_card(reviewed, reviewer="evidence-reviewer", published_at=NOW)
        smoke.save_card(published)

        published_locales = []
        for locale in ("ru",):
            record = smoke.get_translation(card.card_id, locale)
            approved = review_translation(
                record, reviewer="evidence-reviewer", accept=True, now=NOW
            )
            smoke.save_translation(approved)
            smoke.save_translation(
                publish_translation(
                    published, approved, reviewer="evidence-reviewer", now=NOW
                )
            )
            published_locales.append(locale)

        policy = default_project_policy()
        assistant = KnowledgeAssistant(smoke, policy, clock=lambda: NOW)
        viewer = AssistantPrincipal("evidence-viewer", "tenant-evidence", frozenset({"viewer"}))
        admin = AssistantPrincipal("evidence-admin", "tenant-evidence", frozenset({"project_admin"}))

        asks = []
        for locale in SUPPORTED_LOCALES:
            answer = assistant.ask(viewer, QUESTIONS[locale])
            asks.append(
                {
                    "question_locale": locale,
                    **{
                        "kind": answer.kind,
                        "language": answer.language,
                        "source_language": answer.source_language,
                        "response_language": answer.response_language,
                        "content_language": answer.content_language,
                        "translation_status": answer.translation_status,
                        "fallback_used": answer.fallback_used,
                        "card_ids": list(answer.card_ids),
                        "citations": [
                            {"card_id": c.card_id, "source_url": c.source_url}
                            for c in answer.citations
                        ],
                        "message": answer.message[:400],
                    },
                }
            )

        guide = assistant.guide(viewer, published.card_id, "start", language="ru")
        next_step = assistant.guide(viewer, published.card_id, "next", language="ru")
        guide_payload = {
            "language": guide.language,
            "fallback_used": guide.fallback_used,
            "translation_status": guide.translation_status,
            "message": guide.message,
            "next_message": next_step.message,
            "next_step": next_step.next_step,
        }

        workflow = ProjectCreationWorkflow(
            smoke, NullGateway(), policy=policy, clock=lambda: NOW
        )
        workflow_starts = []
        for locale in ("ru", "fa"):
            view = workflow.start(
                admin.workflow_principal(),
                locale=locale,
                request_key=f"evidence-start-{locale}",
            )
            workflow_starts.append(
                {
                    "locale": view.locale,
                    "language_code": view.language_code,
                    "direction": view.direction,
                    "first_step_title": view.steps[0].title,
                    "guidance_items": len(view.guidance),
                    "guidance": list(view.guidance),
                }
            )

        scope = _scope()
        searches = []
        for locale in SUPPORTED_LOCALES:
            outcome = search(smoke, scope, QUESTIONS[locale], limit=3, locale=locale)
            top = outcome.hits[0] if outcome.hits else None
            searches.append(
                {
                    "locale": locale,
                    "query_locale": outcome.query_locale,
                    "response_locale": outcome.response_locale,
                    "hits": len(outcome.hits),
                    "top_title": None if top is None else top.title,
                    "top_language": None if top is None else top.language,
                    "top_translation_status": None if top is None else top.translation_status,
                    "top_fallback_used": None if top is None else top.fallback_used,
                    "evidence": None if top is None else top.evidence,
                }
            )

        _write(
            out / "assistant-smoke.json",
            {
                "contract": "cubi-multilingual-assistant-smoke.v1",
                "database": "disposable copy with one published card and one published Russian translation",
                "card_id": published.card_id,
                "published_translation_locales": published_locales,
                "locales": locale_registry(),
                "asks": asks,
                "guide": guide_payload,
                "workflow_starts": workflow_starts,
                "searches": searches,
            },
        )
        _write(
            out / "seed-report.json",
            {"contract": "cubi-knowledge-translation-seed.v1", "result": seed},
        )
    finally:
        smoke.close()
    return 0


def _scope():
    return SearchScope(
        user_id="evidence-viewer",
        tenant_id="tenant-evidence",
        include_project=False,
        include_user_memory=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
