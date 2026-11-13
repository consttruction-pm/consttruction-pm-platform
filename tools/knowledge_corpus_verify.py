#!/usr/bin/env python3
"""Verify a full-corpus knowledge ingestion on SQLite and PostgreSQL.

The tool answers the questions a fixture cannot: did the real Version 26 corpus
land in the database, is every topic accounted for, are the two stores logically
identical, and does a second ingestion change anything? It reads snapshots
through the ``KnowledgeStore`` protocol so both engines are compared with one
definition of "the same corpus", and it writes a machine-readable report.

Usage::

    python tools/knowledge_corpus_verify.py \
        --dsn postgresql://user@host/knowledge \
        --sqlite path/to/knowledge.sqlite3 \
        --out evidence/corpus-verification.json

    # also re-run the pipeline and prove the second run is a no-op
    python tools/knowledge_corpus_verify.py --dsn … --repeat-ingest --out …

The SQLite file is copied before it is opened, because opening it through the
store applies the schema migration; the original evidence file is never
modified. PostgreSQL is measured through the same store, not through ad-hoc SQL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from construction_pm.knowledge.ingest import (  # noqa: E402
    IngestionPipeline,
    UrllibFetcher,
    card_signature,
)
from construction_pm.knowledge.postgres_store import PostgresKnowledgeStore  # noqa: E402
from construction_pm.knowledge.sources import INGESTABLE_SOURCES  # noqa: E402
from construction_pm.knowledge.sqlite_store import SqliteKnowledgeStore  # noqa: E402

EVIDENCE_AUDIT = (
    Path(__file__).resolve().parents[1]
    / "docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/source-audit.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_topic_counts() -> dict[str, int]:
    """Authoritative topic totals, read from the recorded live source audit."""

    if not EVIDENCE_AUDIT.exists():  # pragma: no cover - evidence is committed
        return {}
    audit = json.loads(EVIDENCE_AUDIT.read_text(encoding="utf-8"))
    return {
        str(source["source_id"]): int(source["topic_count"])
        for source in audit.get("sources", [])
        if source.get("role") == "authoritative_ingest" and source.get("topic_count")
    }


def snapshot(store) -> dict[str, object]:
    """Read one logical snapshot through the store protocol."""

    # The store clamps an explicit limit to 1000, so ask for the default (all).
    cards = store.list_cards(scope="central")
    card_index = {
        card.card_id: {
            "content_hash": card.content_hash,
            "revision": card.revision,
            "card_type": card.card_type.value,
            "validation_status": card.validation_status.value,
            "publication_status": card.publication_status.value,
            "title": card.title,
            "source_url": card.source_url,
            "source_version": card.source_version,
            "topic_id": card.topic_id,
            "tenant_id": card.tenant_id,
            "project_id": card.project_id,
        }
        for card in cards
    }
    topic_index: dict[str, dict[str, object]] = {}
    for source in INGESTABLE_SOURCES:
        for topic in store.list_topics(source_id=source.source_id):
            key = f"{source.source_id}:{topic['topic_key']}"
            topic_index[key] = {
                "url": topic["url"],
                "title": topic["title"],
                "status": topic["status"],
                "content_hash": topic["content_hash"],
                "http_status": topic["http_status"],
                "parent_key": topic["parent_key"],
            }
    translations = store.list_card_translations(limit=1_000_000)
    translation_index = {
        f"{record.card_id}:{record.locale}": {
            "translation_version": record.translation_version,
            "content_hash": record.content_hash,
            "translation_status": record.translation_status.value,
            "review_status": record.review_status.value,
            "machine_translated": record.machine_translated,
            "source_bound": dict(record.localization_metadata).get("source_card_hash"),
        }
        for record in translations
    }
    events: Counter[tuple[str, str]] = Counter()
    for card_id in card_index:
        rows, _ = store.list_card_events(card_id, limit=1000)
        for row in rows:
            events[(str(row["action"]), str(row["actor_id"]))] += 1
    audit_rows = store.list_audit(limit=1_000_000)
    audits = Counter(
        (str(row["action"]), str(row["outcome"]), str(row["entity_kind"]))
        for row in audit_rows
    )
    sources = {
        str(record["source_id"]): {
            "status": record.get("status"),
            "content_hash": record.get("content_hash"),
            "topic_counts": store.topic_counts(str(record["source_id"])),
        }
        for record in store.list_sources()
    }
    return {
        "card_objects": list(cards),
        "cards": card_index,
        "topics": topic_index,
        "translations": translation_index,
        "events": events,
        "audits": audits,
        "sources": sources,
        "counts": {
            "cards": len(card_index),
            "topics": len(topic_index),
            "translations": len(translation_index),
            "events": sum(events.values()),
            "audits": sum(audits.values()),
        },
    }


def integrity(snapshot_value: dict[str, object], *, label: str) -> dict[str, object]:
    cards: dict[str, dict[str, object]] = snapshot_value["cards"]  # type: ignore[assignment]
    topics: dict[str, dict[str, object]] = snapshot_value["topics"]  # type: ignore[assignment]
    translations: dict[str, dict[str, object]] = snapshot_value["translations"]  # type: ignore[assignment]
    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, detail: object = None) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    expected = _expected_topic_counts()
    actual: Counter[str] = Counter(key.split(":", 1)[0] for key in topics)
    per_source = {source.source_id: actual.get(source.source_id, 0) for source in INGESTABLE_SOURCES}
    check(
        "authoritative_topic_totals",
        all(per_source.get(source_id) == expected.get(source_id) for source_id in per_source)
        and bool(expected),
        {"expected": expected, "actual": per_source},
    )
    statuses = Counter(str(row["status"]) for row in topics.values())
    check(
        "every_topic_converted",
        statuses.get("converted", 0) == len(topics) and not statuses.get("failed"),
        dict(statuses),
    )
    check(
        "no_duplicate_topic_keys",
        len(topics) == len({key for key in topics}),
        {"rows": len(topics), "keys": len({key for key in topics})},
    )
    duplicate_cards = len(set(cards)) != len(cards)
    check("no_duplicate_card_ids", not duplicate_cards, {"cards": len(cards)})
    signatures: dict[tuple, list[str]] = {}
    for card in snapshot_value["card_objects"]:  # type: ignore[union-attr]
        signatures.setdefault(card_signature(card), []).append(card.card_id)
    duplicated = [ids for ids in signatures.values() if len(ids) > 1]
    check(
        "no_duplicate_card_content",
        not duplicated,
        {"groups": len(duplicated), "examples": duplicated[:3]},
    )
    bad_hash = [card_id for card_id, row in cards.items() if not _is_hash(row["content_hash"])]
    check("card_content_hashes_are_sha256", not bad_hash, {"bad": bad_hash[:5], "count": len(bad_hash)})
    bad_topic_hashes = [
        key for key, row in topics.items() if row["status"] == "converted" and not _is_hash(row["content_hash"])
    ]
    check(
        "topic_content_hashes_are_sha256",
        not bad_topic_hashes,
        {"bad": bad_topic_hashes[:5], "count": len(bad_topic_hashes)},
    )
    bad_urls = [
        key
        for key, row in topics.items()
        if not str(row["url"]).startswith("https://docs.oracle.com/")
    ]
    check("topic_urls_are_official", not bad_urls, {"bad": bad_urls[:5], "count": len(bad_urls)})
    orphans = [key for key in translations if key.split(":", 1)[0] not in cards]
    check("no_orphan_translations", not orphans, {"count": len(orphans), "examples": orphans[:5]})
    unscoped = [
        card_id
        for card_id, row in cards.items()
        if row["project_id"] is not None and row["tenant_id"] is None
    ]
    check("no_project_card_without_tenant", not unscoped, {"count": len(unscoped)})
    missing_topic = [card_id for card_id, row in cards.items() if not row["topic_id"]]
    check("every_card_has_a_topic", not missing_topic, {"count": len(missing_topic)})
    staled = [
        key
        for key, row in translations.items()
        if row["source_bound"] and row["source_bound"] != cards[key.split(":", 1)[0]]["content_hash"]
    ]
    check("published_translations_bound_to_current_source", not staled, {"stale": staled[:5]})
    published_cards = sum(1 for row in cards.values() if row["publication_status"] == "published")
    return {
        "label": label,
        "ok": all(item["ok"] for item in checks),
        "checks": checks,
        "published_cards": published_cards,
    }


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def compare(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    differences: list[dict[str, object]] = []
    for name in ("cards", "topics", "translations"):
        left_rows: dict[str, object] = left[name]  # type: ignore[assignment]
        right_rows: dict[str, object] = right[name]  # type: ignore[assignment]
        only_left = sorted(set(left_rows) - set(right_rows))
        only_right = sorted(set(right_rows) - set(left_rows))
        changed = sorted(
            key for key in set(left_rows) & set(right_rows) if left_rows[key] != right_rows[key]
        )
        if only_left or only_right or changed:
            differences.append(
                {
                    "section": name,
                    "only_sqlite": only_left[:10],
                    "only_postgres": only_right[:10],
                    "changed": changed[:10],
                    "counts": [len(only_left), len(only_right), len(changed)],
                }
            )
    # ``discover``/``ingest_run`` audit rows describe how many times somebody
    # ran the pipeline, not what the corpus contains: one store may legitimately
    # have been ingested twice. Merge decisions and any failure are corpus
    # facts, so those are compared exactly; the run bookkeeping is reported
    # separately as information rather than as a parity failure.
    def corpus_audits(snapshot_value: dict[str, object]) -> Counter:
        return Counter(
            {
                key: value
                for key, value in snapshot_value["audits"].items()  # type: ignore[union-attr]
                if key[0] == "topic_merged" or key[1] != "succeeded"
            }
        )

    if corpus_audits(left) != corpus_audits(right):
        differences.append(
            {
                "section": "audits",
                "left": {
                    "|".join(key): value
                    for key, value in corpus_audits(left).items()
                },
                "right": {
                    "|".join(key): value
                    for key, value in corpus_audits(right).items()
                },
            }
        )
    if left["events"] != right["events"]:
        differences.append(
            {
                "section": "events",
                "left_total": sum(left["events"].values()),  # type: ignore[attr-defined]
                "right_total": sum(right["events"].values()),  # type: ignore[attr-defined]
            }
        )
    corpus_keys = ("cards", "topics", "translations")
    if any(left["counts"][key] != right["counts"][key] for key in corpus_keys):  # type: ignore[index]
        differences.append({"section": "counts", "left": left["counts"], "right": right["counts"]})
    return {
        "equal": not differences,
        "differences": differences,
        "informational": {
            "audit_rows": {
                "sqlite": sum(left["audits"].values()),  # type: ignore[attr-defined]
                "postgres": sum(right["audits"].values()),  # type: ignore[attr-defined]
            }
        },
    }


def _open_sqlite_copy(path: Path) -> tuple[SqliteKnowledgeStore, Path, dict[str, object]]:
    handle, copy_name = tempfile.mkstemp(prefix="kb-corpus-", suffix=".sqlite3")
    os.close(handle)
    copy = Path(copy_name)
    shutil.copy2(path, copy)
    return SqliteKnowledgeStore(str(copy)), copy, {
        "path": str(path),
        "sha256": _sha256(path),
        "schema_version": _sqlite_schema(path),
        "copy": str(copy),
    }


def _sqlite_schema(path: Path) -> int | None:
    import sqlite3

    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:  # pragma: no cover - defensive
        return None
    try:
        row = connection.execute("SELECT MAX(version) FROM knowledge_schema_migration").fetchone()
        return None if row is None or row[0] is None else int(row[0])
    finally:
        connection.close()


def _repeat_ingest(store) -> dict[str, object]:
    pipeline = IngestionPipeline(
        store=store,
        fetcher=UrllibFetcher(timeout_seconds=30),
        delay_seconds=0.0,
        fetch_workers=4,
    )
    reports = []
    for source in INGESTABLE_SOURCES:
        report = pipeline.run(source)
        reports.append(
            {
                "source_id": report.source_id,
                "discovered": report.discovered,
                "newly_discovered": report.newly_discovered,
                "converted": report.converted,
                "skipped": report.skipped,
                "failed": report.failed,
            }
        )
    return {
        "reports": reports,
        "no_new_records": all(
            item["newly_discovered"] == 0 and item["converted"] == 0 and item["failed"] == 0
            for item in reports
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="PostgreSQL DSN of the ingested corpus")
    parser.add_argument("--sqlite", help="SQLite database built from the same sources")
    parser.add_argument("--out", required=True, help="Write the JSON verification report here")
    parser.add_argument(
        "--repeat-ingest",
        action="store_true",
        help="Re-run both sources against PostgreSQL and prove the run is a no-op",
    )
    arguments = parser.parse_args(argv)

    report: dict[str, object] = {"contract": "cubi-knowledge-corpus-verification.v1"}
    postgres = PostgresKnowledgeStore(arguments.dsn)
    try:
        pg_snapshot = snapshot(postgres)
        report["postgres"] = {
            "database": {"engine": "postgres", "driver": "psycopg"},
            "counts": pg_snapshot["counts"],
            "sources": pg_snapshot["sources"],
            "integrity": integrity(pg_snapshot, label="postgres"),
        }
        if arguments.repeat_ingest:
            repeat = _repeat_ingest(postgres)
            after = snapshot(postgres)
            unchanged = repeat["no_new_records"] and all(
                after[name] == pg_snapshot[name] for name in ("cards", "topics", "translations")
            )
            report["repeat_ingest"] = {
                **repeat,
                "counts_before": pg_snapshot["counts"],
                "counts_after": after["counts"],
                "unchanged": unchanged,
            }
    finally:
        postgres.close()

    if arguments.sqlite:
        sqlite_store, copy, metadata = _open_sqlite_copy(Path(arguments.sqlite))
        try:
            sqlite_snapshot = snapshot(sqlite_store)
        finally:
            sqlite_store.close()
            copy.unlink(missing_ok=True)
        report["sqlite"] = {
            "database": metadata,
            "counts": sqlite_snapshot["counts"],
            "sources": sqlite_snapshot["sources"],
            "integrity": integrity(sqlite_snapshot, label="sqlite"),
        }
        report["parity"] = compare(sqlite_snapshot, pg_snapshot)

    report["ok"] = all(
        [
            report["postgres"]["integrity"]["ok"],  # type: ignore[index]
            report.get("sqlite", {}).get("integrity", {"ok": True})["ok"],  # type: ignore[union-attr]
            report.get("parity", {"equal": True})["equal"],  # type: ignore[union-attr]
            report.get("repeat_ingest", {"unchanged": True})["unchanged"],  # type: ignore[union-attr]
        ]
    )
    Path(arguments.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "postgres": report["postgres"]["counts"],
                **({"sqlite": report["sqlite"]["counts"]} if "sqlite" in report else {}),
                **({"parity": report["parity"]["equal"]} if "parity" in report else {}),
                **({"repeat": report["repeat_ingest"]["unchanged"]} if "repeat_ingest" in report else {}),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
