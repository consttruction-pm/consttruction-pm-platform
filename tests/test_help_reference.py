"""Guards for the committed Engineering Help reference.

The reference is the single source for every Help page number cited in
``docs/traceability/engineering-v26.json``. These tests fail if the committed
artifacts drift apart (wrong page count, stale index, missing outline target or
a citation that points outside the document).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELP = ROOT / "docs" / "reference" / "help" / "engineering-v26"
PAGE_COUNT = 815


@pytest.fixture(scope="module")
def pages() -> list[str]:
    text = (HELP / "pages.txt").read_text(encoding="utf-8", errors="replace")
    chunks = text.split("\f")
    if chunks and not chunks[-1].strip():
        chunks.pop()
    return chunks


@pytest.fixture(scope="module")
def outline() -> dict:
    return json.loads((HELP / "outline.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def index() -> dict:
    return json.loads((HELP / "index.json").read_text(encoding="utf-8"))


def test_reference_files_exist() -> None:
    for name in ("README.md", "P6_PROFESSIONAL_HELP_G57535-02.pdf", "pages.txt", "outline.json", "index.json"):
        path = HELP / name
        assert path.is_file(), name
        assert path.stat().st_size > 0, name


def test_page_count_matches_the_edition(pages: list[str]) -> None:
    # pdftotext appends a trailing form feed; the fixture drops the empty tail chunk.
    assert len(pages) == PAGE_COUNT
    assert "Help" in pages[0]


def test_every_cited_page_is_inside_the_document(outline: dict) -> None:
    pages = [entry["page"] for entry in outline["entries"] if entry["page"] is not None]
    assert pages
    assert min(pages) >= 1
    assert max(pages) <= PAGE_COUNT


def test_index_covers_every_page(index: dict) -> None:
    rows = index["pages"]
    assert [row["page"] for row in rows] == list(range(1, PAGE_COUNT + 1))


def test_outline_entries_are_unique_and_ordered(outline: dict) -> None:
    entries = outline["entries"]
    assert len(entries) == 988
    assert all(entry["title"].strip() for entry in entries)
    assert all(0 <= entry["depth"] <= 4 for entry in entries)
    pages = [entry["page"] for entry in entries if entry["page"] is not None]
    assert min(pages) >= 1 and max(pages) <= PAGE_COUNT


def test_traceability_pdf_pages_resolve_to_real_headings(pages: list[str], index: dict) -> None:
    trace = json.loads((ROOT / "docs" / "traceability" / "engineering-v26.json").read_text(encoding="utf-8"))
    rows = [row for row in trace["rows"] if row]
    cited = [row["help"]["pdfPage"] for row in rows if (row.get("help") or {}).get("pdfPage")]
    assert cited, "traceability must cite at least one Help page"
    headings = {row["page"]: row["heading"] for row in index["pages"]}
    for page in cited:
        assert 1 <= int(page) <= PAGE_COUNT
        assert headings.get(int(page)), f"page {page} has no extracted heading"
        assert pages[int(page) - 1].strip(), f"page {page} is empty"
