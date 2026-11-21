#!/usr/bin/env python3
"""Verify the official Help references used by CUBI traceability documents.

The CUBI traceability JSON files are the single source of truth for the
page ↔ Help mapping. Every row cites an official Help topic; this script proves
that the URL resolves, that the topic is listed in the official Table of
Contents, and that the recorded title matches the page title.

Nothing here touches product code or the database. It only reads the public
Oracle documentation and the repository JSON.

Usage
-----
    python scripts/verify_help_traceability.py                 # full network check
    python scripts/verify_help_traceability.py --toc-only      # TOC membership only
    python scripts/verify_help_traceability.py --out report.json

Exit code 0 means every row passed. Exit code 1 means at least one row has a
broken URL, a missing TOC entry or a title mismatch; the report names each one.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRACEABILITY = ROOT / "docs" / "traceability"

BASELINES = {
    "engineering": {
        "toc": "https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",
        "prefix": "https://docs.oracle.com/cd/G48902_01/client_help/en_US/",
        "json": TRACEABILITY / "engineering-v26.json",
    },
    "enterprise": {
        "toc": "https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm",
        "prefix": "https://docs.oracle.com/cd/G48897_01/p6help/en/",
        "json": TRACEABILITY / "enterprise-v26.json",
    },
}

USER_AGENT = "CUBI-help-traceability-verifier/1.0 (+documentation verification)"
ANCHOR = re.compile(r'<a[^>]+href="([^"#][^"]*)"[^>]*>(.*?)</a>', re.S | re.I)
TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")


@dataclass
class RowResult:
    environment: str
    row_id: str
    page: str
    surface: str
    url: str
    recorded_title: str
    http_status: int | None = None
    page_title: str | None = None
    toc_title: str | None = None
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def fetch(url: str, *, timeout: float = 20.0, attempts: int = 3) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            return error.code, ""
        except Exception as error:  # network hiccup: retry briefly
            last = error
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"UNREACHABLE: {last}")


def clean(value: str) -> str:
    return html.unescape(TAG.sub(" ", value)).replace("\xa0", " ").strip()


def parse_toc(raw: str, prefix: str) -> dict[str, str]:
    """Map absolute topic URL -> title as printed in the official TOC."""

    entries: dict[str, str] = {}
    for href, text in ANCHOR.findall(raw):
        title = re.sub(r"\s+", " ", clean(text))
        if not title:
            continue
        absolute = href if href.startswith("http") else prefix + href
        # First occurrence wins: the TOC lists a topic once under its section.
        entries.setdefault(absolute, title)
    return entries


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def verify_row(environment: str, row: dict[str, Any], toc: dict[str, str]) -> RowResult:
    help_block = row.get("help") or {}
    result = RowResult(
        environment=environment,
        row_id=row.get("id", ""),
        page=row.get("page", ""),
        surface=row.get("surface", ""),
        url=help_block.get("url", ""),
        recorded_title=help_block.get("title", ""),
    )
    url = result.url
    if not url:
        if row.get("status") in {"CUBI_OWNED", "LEGAL"} and row.get("helpRationale"):
            return result  # intentionally has no official topic
        result.problems.append("NO_HELP_URL")
        return result
    if url not in toc:
        result.problems.append("NOT_IN_OFFICIAL_TOC")
    else:
        result.toc_title = toc[url]
    try:
        status, body = fetch(url)
    except RuntimeError as error:
        result.problems.append(str(error))
        return result
    result.http_status = status
    if status != 200:
        result.problems.append(f"HTTP_{status}")
        return result
    match = TITLE.search(body)
    result.page_title = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip() if match else None
    expected = result.toc_title or result.recorded_title
    if result.page_title and expected:
        page = normalize_title(result.page_title)
        wanted = normalize_title(expected)
        # The page title often appends the product name; require containment.
        if wanted not in page and page not in wanted:
            result.problems.append(
                f"TITLE_MISMATCH recorded={result.recorded_title!r} page={result.page_title!r}"
            )
    return result


def load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["rows"] if isinstance(data, dict) else data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toc-only", action="store_true", help="skip per-topic HTTP fetches")
    parser.add_argument("--environment", choices=sorted(BASELINES), action="append")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", default="")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    environments = args.environment or list(BASELINES)
    results: list[RowResult] = []
    toc_summary: dict[str, int] = {}
    for environment in environments:
        baseline = BASELINES[environment]
        status, body = fetch(baseline["toc"])
        if status != 200:
            print(f"{environment}: TOC HTTP {status}", file=sys.stderr)
            return 1
        toc = parse_toc(body, baseline["prefix"])
        toc_summary[environment] = len(toc)
        rows = load_rows(baseline["json"])
        if args.toc_only:
            for row in rows:
                results.append(check_toc_only(environment, row, toc))
        else:
            with ThreadPoolExecutor(max_workers=max(1, min(8, args.workers))) as pool:
                results.extend(pool.map(lambda row: verify_row(environment, row, toc), rows))

    failures = [item for item in results if not item.ok]
    if not args.quiet:
        for environment in environments:
            subset = [item for item in results if item.environment == environment]
            bad = [item for item in subset if not item.ok]
            print(
                f"{environment}: {len(subset) - len(bad)}/{len(subset)} rows verified "
                f"({toc_summary.get(environment, 0)} TOC topics)"
            )
            for item in bad:
                print(f"  {item.row_id}: {item.url or '(none)'} -> {'; '.join(item.problems)}")
    report = {
        "tool": "verify_help_traceability.py",
        "mode": "toc-only" if args.toc_only else "full",
        "toc_topics": toc_summary,
        "rows": len(results),
        "verified": len(results) - len(failures),
        "failed": len(failures),
        "results": [
            {
                "environment": item.environment,
                "id": item.row_id,
                "page": item.page,
                "surface": item.surface,
                "url": item.url,
                "recorded_title": item.recorded_title,
                "toc_title": item.toc_title,
                "page_title": item.page_title,
                "http_status": item.http_status,
                "problems": item.problems,
            }
            for item in results
        ],
    }
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if not args.quiet:
            print(f"report: {args.out}")
    return 0 if not failures else 1


def check_toc_only(environment: str, row: dict[str, Any], toc: dict[str, str]) -> RowResult:
    help_block = row.get("help") or {}
    result = RowResult(
        environment=environment,
        row_id=row.get("id", ""),
        page=row.get("page", ""),
        surface=row.get("surface", ""),
        url=help_block.get("url", ""),
        recorded_title=help_block.get("title", ""),
    )
    if not result.url:
        if row.get("status") in {"CUBI_OWNED", "LEGAL"} and row.get("helpRationale"):
            return result
        result.problems.append("NO_HELP_URL")
        return result
    result.toc_title = toc.get(result.url)
    if result.toc_title is None:
        result.problems.append("NOT_IN_OFFICIAL_TOC")
    elif normalize_title(result.recorded_title) not in normalize_title(result.toc_title) and normalize_title(
        result.toc_title
    ) not in normalize_title(result.recorded_title):
        result.problems.append(
            f"TOC_TITLE_MISMATCH recorded={result.recorded_title!r} toc={result.toc_title!r}"
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
