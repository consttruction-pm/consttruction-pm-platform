#!/usr/bin/env python3
"""Look up the committed Engineering Help reference (V26, 815 pages).

The PDF and its extracted text live in ``docs/reference/help/engineering-v26``
so the reference survives every session without re-uploading it. This tool is
the only supported way to read it, which keeps page numbers and topic titles
consistent with ``docs/traceability/engineering-v26.json``.

Usage:
    python3 tools/help_pdf_lookup.py page 271
    python3 tools/help_pdf_lookup.py search "leveling" --limit 5
    python3 tools/help_pdf_lookup.py topic "Scheduling Projects"
    python3 tools/help_pdf_lookup.py chapters
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELP = ROOT / "docs" / "reference" / "help" / "engineering-v26"


def _text() -> str:
    return (HELP / "pages.txt").read_text(encoding="utf-8", errors="replace")


def _index() -> dict:
    return json.loads((HELP / "index.json").read_text(encoding="utf-8"))


def _outline() -> dict:
    return json.loads((HELP / "outline.json").read_text(encoding="utf-8"))


def page(number: int) -> int:
    pages = _text().split("\f")
    if not 1 <= number <= len(pages) - 1:
        print(f"page {number} outside 1..{len(pages) - 1}", file=sys.stderr)
        return 2
    print(f"===== page {number} =====")
    print(pages[number - 1].rstrip())
    return 0


def search(term: str, limit: int) -> int:
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    pages = _text().split("\f")
    hits = 0
    for number, body in enumerate(pages, start=1):
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        matches = [line for line in lines if pattern.search(line)]
        if not matches:
            continue
        hits += 1
        print(f"[page {number}] {matches[0][:160]}")
        for extra in matches[1:3]:
            print(f"           {extra[:160]}")
        if hits >= limit:
            break
    if not hits:
        print(f"no match for {term!r}", file=sys.stderr)
        return 1
    return 0


def topic(title: str) -> int:
    entries = _outline()["entries"]
    pattern = re.compile(re.escape(title), re.IGNORECASE)
    found = [e for e in entries if pattern.search(e["title"])]
    if not found:
        print(f"topic {title!r} not in the outline; use search", file=sys.stderr)
        return 1
    for entry in found[:20]:
        indent = "  " * entry["depth"]
        print(f"{indent}{entry['title']}  -> p. {entry['page']}")
    return 0


def chapters() -> int:
    for chapter in _index()["chapters"]:
        print(f"Chapter {chapter['number']:>2}  p. {chapter['page']:>3}  {chapter['runningHeader']}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_page = sub.add_parser("page")
    p_page.add_argument("number", type=int)
    p_search = sub.add_parser("search")
    p_search.add_argument("term")
    p_search.add_argument("--limit", type=int, default=8)
    p_topic = sub.add_parser("topic")
    p_topic.add_argument("title")
    sub.add_parser("chapters")
    args = parser.parse_args(argv)
    if args.command == "page":
        return page(args.number)
    if args.command == "search":
        return search(args.term, args.limit)
    if args.command == "topic":
        return topic(args.title)
    return chapters()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
