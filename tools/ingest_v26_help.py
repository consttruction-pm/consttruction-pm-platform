#!/usr/bin/env python3
"""Ingest the official Version 26 HTML Help into a CUBI knowledge database.

Usage examples::

    python tools/ingest_v26_help.py --db data/knowledge.sqlite3
    python tools/ingest_v26_help.py --dsn postgresql://user@host/knowledge
    python tools/ingest_v26_help.py --db data/knowledge.sqlite3 --max-pages 20
    python tools/ingest_v26_help.py --db data/knowledge.sqlite3 --source p6-26-user-guide
    python tools/ingest_v26_help.py --db data/knowledge.sqlite3 --coverage-out coverage.json

Only the two authoritative Version 26 HTML sources are supported. The command
is resumable: completed pages are skipped unless ``--force`` is supplied.
``--dsn`` ingests into the PostgreSQL store instead of SQLite; both stores share
one implementation of the ingestion rules, so the output must be equivalent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from construction_pm.knowledge.ingest import IngestionPipeline, UrllibFetcher  # noqa: E402
from construction_pm.knowledge.sources import (  # noqa: E402
    INGESTABLE_SOURCES,
    get_source,
)
from construction_pm.knowledge.sqlite_store import SqliteKnowledgeStore  # noqa: E402


def _open_store(args: argparse.Namespace):
    if args.dsn:
        from construction_pm.knowledge.postgres_store import PostgresKnowledgeStore

        return PostgresKnowledgeStore(args.dsn)
    return SqliteKnowledgeStore(args.db)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--db", help="Path to the knowledge SQLite database")
    target.add_argument(
        "--dsn",
        help="PostgreSQL DSN; the schema is migrated before ingestion",
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=[source.source_id for source in INGESTABLE_SOURCES],
        help="Ingest only the named source (repeatable)",
    )
    parser.add_argument("--max-pages", type=int, default=None, help="Limit pages per source")
    parser.add_argument("--force", action="store_true", help="Re-fetch converted pages")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between requests")
    parser.add_argument(
        "--fetch-workers",
        type=int,
        default=8,
        help="Parallel HTTP fetches; parsing and writes stay ordered",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument("--coverage-out", help="Write the coverage report JSON here")
    parser.add_argument("--report-out", help="Write ingestion reports JSON here")
    args = parser.parse_args(argv)

    selected = (
        tuple(get_source(source_id) for source_id in args.source)
        if args.source
        else INGESTABLE_SOURCES
    )
    store = _open_store(args)
    try:
        pipeline = IngestionPipeline(
            store=store,
            fetcher=UrllibFetcher(timeout_seconds=args.timeout),
            delay_seconds=max(0.0, args.delay),
            fetch_workers=max(1, args.fetch_workers),
        )
        reports = []
        for source in selected:
            report = pipeline.run(
                source,
                max_pages=args.max_pages,
                force=args.force,
                progress=lambda item: print(
                    f"[{item.get('status')}] {item.get('topic_key')} "
                    f"({item.get('processed')} processed, {item.get('failed')} failed)",
                    file=sys.stderr,
                ),
            )
            reports.append(report.as_dict())
            print(
                f"{source.source_id}: discovered={report.discovered} "
                f"new={report.newly_discovered} converted={report.converted} "
                f"skipped={report.skipped} failed={report.failed}"
            )
        coverage = pipeline.coverage_report()
        if args.coverage_out:
            Path(args.coverage_out).write_text(
                json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        if args.report_out:
            Path(args.report_out).write_text(
                json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        failures = sum(report["failed"] for report in reports)
        outstanding = sum(
            len(source["unconverted_topics"]) for source in coverage["sources"]
        )
        return 1 if failures or outstanding else 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
