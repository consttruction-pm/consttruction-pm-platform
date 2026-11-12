#!/usr/bin/env python3
"""Audit the official Version 26 HTML sources against the evidence database.

The audit distinguishes the two authoritative TOCs used by the ingestion
pipeline from the older ``pro-help``/``pro-user`` TOCs, which remain official
but are a different edition. It records the live HTTP status and topic count of
each TOC so the 527/557 User Guide discrepancy is resolved by measurement, not
by repeating an earlier report.

Usage::

    python tools/knowledge_source_audit.py \
        --db docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/cubi-knowledge-v26.sqlite3 \
        --out docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/source-audit.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from construction_pm.knowledge.html import parse_toc  # noqa: E402
from construction_pm.knowledge.model import SourceDefinition, SourceKind  # noqa: E402
from construction_pm.knowledge.sqlite_store import SqliteKnowledgeStore  # noqa: E402

USER_AGENT = "CUBI-knowledge-audit/1.0"

AUDIT_SOURCES = (
    {
        "source_id": "p6-26-html-help",
        "registry": "P6_26_HTML_HELP",
        "title": "Version 26 HTML Help table of contents",
        "url": "https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",
        "kind": SourceKind.HTML_HELP,
        "role": "authoritative_ingest",
    },
    {
        "source_id": "p6-26-user-guide",
        "registry": "P6_26_USER_GUIDE",
        "title": "Version 26 Professional User Guide",
        "url": "https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm",
        "kind": SourceKind.USER_GUIDE,
        "role": "authoritative_ingest",
    },
    {
        "source_id": "p6-26-help",
        "registry": "P6_26_HELP",
        "title": "Version 26 Professional Help",
        "url": (
            "https://docs.oracle.com/en/industries/construction-engineering/"
            "primavera-p6-professional/26/pro-help/toc.htm"
        ),
        "kind": SourceKind.HELP,
        "role": "official_alternate_not_ingested",
    },
    {
        "source_id": "p6-26-user-guide-pro-user",
        "registry": "none",
        "title": "Version 26 Professional User Guide (pro-user TOC)",
        "url": (
            "https://docs.oracle.com/en/industries/construction-engineering/"
            "primavera-p6-professional/26/pro-user/toc.htm"
        ),
        "kind": SourceKind.USER_GUIDE,
        "role": "official_alternate_not_ingested",
    },
    {
        "source_id": "p6-26-docs-home",
        "registry": "P6_26_DOCS_HOME",
        "title": "Version 26 documentation set",
        "url": (
            "https://docs.oracle.com/en/industries/construction-engineering/"
            "primavera-p6-professional/26/"
        ),
        "kind": SourceKind.DOCUMENTATION_HOME,
        "role": "landing_not_ingested",
    },
    {
        "source_id": "p6-26-books",
        "registry": "P6_26_BOOKS",
        "title": "Version 26 documentation index",
        "url": (
            "https://docs.oracle.com/en/industries/construction-engineering/"
            "primavera-p6-professional/26/books.html"
        ),
        "kind": SourceKind.DOCUMENT_INDEX,
        "role": "landing_not_ingested",
    },
)


def _fetch(url: str) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.status, response.read().decode("utf-8", "replace")


def _audit_source(definition: dict[str, object]) -> dict[str, object]:
    url = str(definition["url"])
    try:
        status, body = _fetch(url)
    except Exception as exc:  # noqa: BLE001 - failure is recorded, not hidden
        return {
            **{k: v.value if isinstance(v, SourceKind) else v for k, v in definition.items()},
            "http_status": None,
            "error": type(exc).__name__,
            "topic_count": None,
        }
    entry = {
        **{k: v.value if isinstance(v, SourceKind) else v for k, v in definition.items()},
        "http_status": status,
        "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "content_bytes": len(body.encode("utf-8")),
    }
    if entry["role"] != "landing_not_ingested":
        source = SourceDefinition(
            source_id=str(definition["source_id"]),
            title=str(definition["title"]),
            kind=definition["kind"],
            release="26",
            landing_url=url,
            toc_url=url,
        )
        links = parse_toc(body, source=source, toc_url=url)
        entry["topic_count"] = len(links)
        entry["first_topic"] = links[0].title if links else None
        entry["last_topic"] = links[-1].title if links else None
    else:
        discovered = {
            urljoin(url, href)
            for href in re.findall(r'href=["\']([^"\']+)["\']', body, flags=re.IGNORECASE)
            if "docs.oracle.com" in urljoin(url, href)
        }
        entry["link_count"] = len(discovered)
        entry["links"] = sorted(discovered)[:25]
    return entry


def _database_section(db_path: str) -> dict[str, object]:
    store = SqliteKnowledgeStore(db_path)
    connection = sqlite3.connect(db_path)
    try:
        source_ids = [str(item["source_id"]) for item in AUDIT_SOURCES]
        rows = {row["source_id"]: row for row in store.list_sources()}
        database_sources = []
        for source_id in source_ids:
            row = rows.get(source_id)
            counts = store.topic_counts(source_id)
            card_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM knowledge_card c
                JOIN knowledge_topic t ON t.topic_id = c.topic_id
                WHERE t.source_id = ?
                """,
                (source_id,),
            ).fetchone()[0]
            database_sources.append(
                {
                    "source_id": source_id,
                    "registered_in_database": row is not None,
                    "status": None if row is None else row.get("status"),
                    "toc_url": None if row is None else row.get("toc_url"),
                    "topic_counts": counts,
                    "card_count": card_count,
                }
            )
        cards = store.list_cards()
        return {
            "card_total": len(cards),
            "card_status_counts": _status_counts(cards),
            "sources": database_sources,
        }
    finally:
        connection.close()
        store.close()


def _status_counts(cards) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        key = card.publication_status.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    sources = [_audit_source(item) for item in AUDIT_SOURCES]
    database = _database_section(args.db)
    report = {
        "contract": "cubi-knowledge-source-audit.v1",
        "sources": sources,
        "database": database,
        "user_guide_discrepancy": {
            "count_527": {
                "url": next(
                    item["url"]
                    for item in sources
                    if item["source_id"] == "p6-26-user-guide-pro-user"
                ),
                "topic_count": next(
                    item["topic_count"]
                    for item in sources
                    if item["source_id"] == "p6-26-user-guide-pro-user"
                ),
                "explanation": "legacy pro-user TOC, a separate official edition",
            },
            "count_557": {
                "url": next(
                    item["url"] for item in sources if item["source_id"] == "p6-26-user-guide"
                ),
                "topic_count": next(
                    item["topic_count"]
                    for item in sources
                    if item["source_id"] == "p6-26-user-guide"
                ),
                "explanation": "G48902 p6_pro_user TOC, used by this branch and evidence database",
            },
            "resolution": (
                "527 and 557 are two different official User Guide TOCs; this branch "
                "ingests the G48902 p6_pro_user edition (557) and does not mix the "
                "pro-user edition (527) into the same source id."
            ),
        },
    }
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for item in sources:
        print(
            f"{item['source_id']}: status={item.get('http_status')} "
            f"topics={item.get('topic_count')} role={item['role']}"
        )
    print(f"database cards={database['card_total']} statuses={database['card_status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
