"""Deterministic HTML Help parser for the Version 26 knowledge pipeline.

The parser is intentionally dependency-free and conservative: it extracts only
what the page really contains and never infers a field, menu or step that is not
present. Boilerplate navigation, search widgets and publication stamps are
dropped so a card cannot cite navigation chrome as engineering content.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterable, Sequence
from urllib.parse import urljoin, urlsplit

from .model import (
    ContentBlock,
    KnowledgeError,
    ParsedTopic,
    TopicLink,
    detect_language,
    merge_unique,
    sha256_hex,
    text,
    topic_id_for,
)
from .sources import SourceDefinition, resolve_topic_url, topic_key_for

_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_BOILERPLATE_PREFIXES = (
    "last published",
    "javascript must be enabled",
    "search only in titles",
    "copyright ©",
    "copyright 19",
    "about consent notices",
    "table of contents",
)
_BOILERPLATE_EXACT = frozenset({"previous", "next", "copyright"})
_PREREQUISITE = re.compile(
    r"prerequisit|before you (?:begin|start)|required (?:before|information|fields)|you need",
    re.IGNORECASE,
)
_WARNING = re.compile(
    r"\bwarn|\bcaution|\bimportant|\battention|\bnote\b|\bconsideration|\btip\b",
    re.IGNORECASE,
)
_OPTION = re.compile(
    r"\boption|\bfield|\bsetting|\bpreference|\btab\b|\bcolumn|\bdisplay\b|\bfilter\b",
    re.IGNORECASE,
)
_LIMITATION = re.compile(
    r"\blimit|\brestrict|\bnot supported|\bcannot\b|\bcan't\b|\bonly if\b|\bnote that\b|\bnot available\b",
    re.IGNORECASE,
)
_INLINE_NOTE = re.compile(r"^(note|caution|warning|important|tip)\b\s*[:\-]", re.IGNORECASE)
_SUBHEAD_LEVELS = {"subhead1": 3, "subhead2": 4, "subhead3": 5}
_THIN_CONTENT_LIMITATION = (
    "Official source page contains no body content beyond its heading; "
    "no procedure or detail was extracted from this page."
)
_MAX_BLOCKS = 2_000
_MAX_LINKS = 500


@dataclass(frozen=True)
class ParsedPage:
    title: str
    breadcrumb: tuple[str, ...]
    headings: tuple[tuple[int, str], ...]
    blocks: tuple[ContentBlock, ...]
    links: tuple[str, ...]
    document_id: str | None = None
    published_date: str | None = None


@dataclass
class _Capture:
    tag: str
    level: int | None = None
    ordered: bool = False
    ordinal: int | None = None
    parts: list[str] = field(default_factory=list)
    link_hrefs: list[str] = field(default_factory=list)
    ignored: bool = False


class _HelpHtmlParser(HTMLParser):
    def __init__(self, *, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.article_seen = False
        self.in_article = False
        self.article_depth = 0
        self.skip_depth = 0
        self.breadcrumb_depth = 0
        self.capture: _Capture | None = None
        self.enumeration_depth = 0
        self.headings: list[tuple[int, str]] = []
        self.blocks: list[ContentBlock] = []
        self.links: list[str] = []
        self.breadcrumb: list[str] = []
        self.section: str | None = None
        self.list_stack: list[list[object]] = []
        self.row_cells: list[str] = []
        self.cell_capture: _Capture | None = None
        self.title: str | None = None
        self.document_id: str | None = None
        self.published_date: str | None = None

    # -- helpers ---------------------------------------------------------
    def _flush(self) -> None:
        capture = self.capture
        self.capture = None
        if capture is None or capture.ignored:
            return
        value = _clean(" ".join(capture.parts))
        if not value or _is_boilerplate(value):
            return
        if capture.level is not None:
            level = int(capture.level)
            self.headings.append((level, value))
            if self.title is None and level <= 2:
                self.title = value
            self.section = value
            self._append_block(ContentBlock("heading", value, section=None, level=level))
            return
        if capture.tag == "li":
            kind = "step" if capture.ordered else "bullet"
            self._append_block(
                ContentBlock(
                    kind,
                    value,
                    section=self.section,
                    ordinal=capture.ordinal,
                )
            )
            return
        if capture.tag == "p":
            kind = "note" if _INLINE_NOTE.match(value) or (
                self.section and _WARNING.search(self.section)
            ) else "paragraph"
            self._append_block(ContentBlock(kind, value, section=self.section))
            return
        if capture.tag in {"td", "th"}:
            self.cell_capture = None
            self.row_cells.append(value)
            return
        self._append_block(ContentBlock("paragraph", value, section=self.section))

    def _append_block(self, block: ContentBlock) -> None:
        if len(self.blocks) >= _MAX_BLOCKS:
            return
        self.blocks.append(block)

    def _start_capture(self, tag: str, **kwargs: object) -> None:
        self._flush()
        self.capture = _Capture(tag=tag, **kwargs)  # type: ignore[arg-type]

    # -- parser callbacks ------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        if tag == "article":
            self.article_seen = True
            self.in_article = True
            self.article_depth += 1
            return
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if not self._active():
            return
        if tag == "meta":
            name = attributes.get("name", "").lower()
            if name == "aitobjectid" and attributes.get("content"):
                self.document_id = attributes["content"].strip()
            if name == "dcterms.created" and attributes.get("content"):
                self.published_date = attributes["content"].strip()
            return
        if tag == "span":
            if self.enumeration_depth:
                self.enumeration_depth += 1
                return
            if self.capture is not None and self.capture.tag in _HEADINGS:
                classes = attributes.get("class", "").split()
                if any(name.startswith("enumeration_") for name in classes):
                    # Chapter/section ordinals are rendered inside headings as
                    # a styled span; they are navigation labels, not the title.
                    self.enumeration_depth = 1
                    return
        if tag in {"ol", "ul"}:
            self._flush()
            self.list_stack.append([tag, 0])
            return
        if tag in {"div", "section"} and (
            attributes.get("id") == "breadcrumb"
            or "breadcrumb" in attributes.get("class", "")
        ):
            self.breadcrumb_depth += 1
            return
        if tag in _HEADINGS:
            classes = attributes.get("class", "").split()
            self._start_capture(
                tag,
                level=_HEADINGS[tag],
                ignored="docinfo" in classes,
            )
            return
        if tag == "p":
            classes = attributes.get("class", "").split()
            level = next(
                (_SUBHEAD_LEVELS[name] for name in classes if name in _SUBHEAD_LEVELS),
                None,
            )
            self._start_capture(tag, level=level)
            return
        if tag == "li":
            ordered = bool(self.list_stack and self.list_stack[-1][0] == "ol")
            ordinal = None
            if ordered and self.list_stack:
                self.list_stack[-1][1] = int(self.list_stack[-1][1]) + 1  # type: ignore[arg-type]
                ordinal = int(self.list_stack[-1][1])
            self._start_capture(tag, ordered=ordered, ordinal=ordinal)
            return
        if tag == "tr":
            self._flush()
            self.row_cells = []
            return
        if tag in {"td", "th"}:
            self._flush()
            self.cell_capture = _Capture(tag=tag)
            self.capture = self.cell_capture
            return
        if tag == "a":
            href = attributes.get("href", "").strip()
            if href and href not in {"#", "javascript:void(0)"}:
                if len(self.links) < _MAX_LINKS:
                    resolved = urljoin(self.base_url, href)
                    if resolved.startswith("https://"):
                        self.links.append(resolved.split("#", 1)[0])
                if self.capture is not None:
                    self.capture.link_hrefs.append(href)
            return
        if tag == "br" and self.capture is not None:
            self.capture.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "article":
            if self.article_depth:
                self.article_depth -= 1
            if self.article_depth == 0:
                self.in_article = False
            return
        if tag in {"script", "style", "noscript"}:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if not self._active():
            return
        if tag == "span" and self.enumeration_depth:
            self.enumeration_depth -= 1
            return
        if tag in {"ol", "ul"}:
            self._flush()
            if self.list_stack:
                self.list_stack.pop()
            return
        if tag in {"div", "section"} and self.breadcrumb_depth:
            self.breadcrumb_depth -= 1
            return
        if tag in _HEADINGS or tag == "p" or tag == "li":
            self._flush()
            return
        if tag in {"td", "th"}:
            self._flush()
            return
        if tag == "tr":
            self._flush()
            cells = [cell for cell in self.row_cells if cell]
            if cells:
                self._append_block(
                    ContentBlock("table", " | ".join(cells), section=self.section)
                )
            self.row_cells = []

    def handle_data(self, data: str) -> None:
        if not self._active() or self.skip_depth or self.enumeration_depth:
            return
        if self.capture is not None and data.strip():
            self.capture.parts.append(data)
            if self.breadcrumb_depth and self.capture.tag == "a":
                cleaned = _clean(data)
                if cleaned and not _is_boilerplate(cleaned):
                    self.breadcrumb.append(cleaned)
        elif self.breadcrumb_depth and data.strip():
            cleaned = _clean(data)
            if cleaned and not _is_boilerplate(cleaned) and cleaned not in self.breadcrumb:
                # Breadcrumb containers often put separators in plain text.
                if len(cleaned) < 120 and cleaned not in {"|", ">", "/"}:
                    self.breadcrumb.append(cleaned)

    def _active(self) -> bool:
        return self.in_article or not self.article_seen

    def close(self) -> None:
        super().close()
        self._flush()


def _clean(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def _is_boilerplate(value: str) -> bool:
    lowered = value.lower().strip(" .:")
    if len(value) < 2:
        return True
    if lowered in _BOILERPLATE_EXACT:
        return True
    return any(lowered.startswith(prefix) for prefix in _BOILERPLATE_PREFIXES) and len(value) < 160


def parse_help_page(html: str, *, url: str) -> ParsedPage:
    if not isinstance(html, str):
        raise KnowledgeError("KNOWLEDGE_HTML_INVALID")
    parser = _HelpHtmlParser(base_url=url)
    parser.feed(html)
    parser.close()
    title = parser.title
    if title is None:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            title = _clean(re.sub(r"<[^>]+>", " ", match.group(1)))
    if not title:
        raise KnowledgeError("KNOWLEDGE_TOPIC_TITLE_MISSING")
    breadcrumb = tuple(merge_unique(parser.breadcrumb, limit=20))
    return ParsedPage(
        title=title,
        breadcrumb=breadcrumb,
        headings=tuple(parser.headings),
        blocks=tuple(parser.blocks),
        links=tuple(dict.fromkeys(parser.links)),
        document_id=parser.document_id,
        published_date=parser.published_date,
    )


def _section_matches(section: str | None, pattern: re.Pattern[str]) -> bool:
    return bool(section and pattern.search(section))


def build_parsed_topic(
    page: ParsedPage,
    *,
    source: SourceDefinition,
    url: str,
    parent_key: str | None = None,
    known_topic_urls: Iterable[str] = (),
    title_override: str | None = None,
) -> ParsedTopic:
    """Convert one parsed page into a validated, provenance-carrying topic."""

    topic_key = topic_key_for(source, url)
    title = _clean(title_override) if title_override else page.title
    blocks = page.blocks
    steps = tuple(
        block.text
        for block in blocks
        if block.kind == "step" and not _section_matches(block.section, _WARNING)
    )
    prerequisites = merge_unique(
        block.text
        for block in blocks
        if block.kind in {"paragraph", "bullet"}
        and (
            _section_matches(block.section, _PREREQUISITE)
            or block.text.lower().startswith(("before you begin", "prerequisite"))
        )
    )
    warnings = merge_unique(
        block.text
        for block in blocks
        if block.kind == "note"
        or _section_matches(block.section, _WARNING)
        or _INLINE_NOTE.match(block.text)
    )
    options = merge_unique(
        block.text
        for block in blocks
        if block.kind in {"bullet", "table", "paragraph"}
        and _section_matches(block.section, _OPTION)
        and block.text not in steps
    )
    limitations = merge_unique(
        block.text
        for block in blocks
        if _LIMITATION.search(block.text)
        and not _INLINE_NOTE.match(block.text)
        and block.text not in warnings
    )
    if not any(
        block.kind != "heading" and block.text.strip() for block in blocks
    ):
        # Stub pages are real official entries but carry no extractable detail.
        # Record that fact instead of letting the heading masquerade as content.
        limitations = merge_unique([*limitations, _THIN_CONTENT_LIMITATION])

    same_source_urls = {candidate.split("#", 1)[0] for candidate in known_topic_urls}
    related: list[str] = []
    for link in page.links:
        if link == url.split("#", 1)[0]:
            continue
        if same_source_urls and link not in same_source_urls:
            continue
        try:
            related.append(topic_key_for(source, link))
        except KnowledgeError:
            continue

    word_count = len(
        " ".join([title, *(block.text for block in blocks)]).split()
    )
    canonical = json.dumps(
        {
            "title": title,
            "breadcrumb": list(page.breadcrumb),
            "blocks": [block.as_dict() for block in blocks],
            "steps": list(steps),
            "prerequisites": list(prerequisites),
            "warnings": list(warnings),
            "options": list(options),
            "limitations": list(limitations),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    parsed = ParsedTopic(
        topic_id=topic_id_for(source.source_id, topic_key),
        source_id=source.source_id,
        topic_key=topic_key,
        url=url,
        title=title,
        language=detect_language(title + " " + " ".join(block.text for block in blocks if block.kind == "paragraph")),
        content_hash=sha256_hex(canonical),
        parent_key=parent_key,
        breadcrumb=page.breadcrumb,
        headings=page.headings,
        blocks=blocks,
        steps=steps,
        prerequisites=prerequisites,
        warnings=warnings,
        options=options,
        limitations=limitations,
        related=merge_unique(related, limit=100),
        word_count=word_count,
    )
    parsed.validate()
    return parsed


def parse_toc(
    html: str,
    *,
    source: SourceDefinition,
    toc_url: str,
) -> tuple[TopicLink, ...]:
    """Parse a nested official table of contents into a flat, ordered list.

    Both the modern DITA-generated TOC and the legacy HTML Help TOC use nested
    ``ul/li/a`` markup, so one tolerant scanner covers both shapes.
    """

    if not isinstance(html, str) or not html.strip():
        raise KnowledgeError("KNOWLEDGE_TOC_EMPTY")
    article_start = html.lower().find("<article")
    body = html[article_start:] if article_start >= 0 else html
    tokens = re.finditer(
        r"<(?P<tag>/?(?:ul|ol|li|a))\b(?P<attrs>[^>]*)>"
        r"|<[^>]*>"
        r"|(?P<text>[^<]+)",
        body,
        re.IGNORECASE,
    )
    depth = 0
    pending_href: str | None = None
    pending_title: list[str] | None = None
    stack: list[tuple[int, str]] = []
    links: list[TopicLink] = []
    seen: set[str] = set()
    for token in tokens:
        tag = (token.group("tag") or "").lower()
        if tag in {"ul", "ol"}:
            depth += 1
            continue
        if tag in {"/ul", "/ol"}:
            depth = max(0, depth - 1)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            continue
        if tag == "a":
            attrs = token.group("attrs") or ""
            match = re.search(r'href\s*=\s*"([^"]+)"', attrs, re.IGNORECASE)
            if match is None:
                match = re.search(r"href\s*=\s*'([^']+)'", attrs, re.IGNORECASE)
            if match is None:
                continue
            pending_href = match.group(1).strip()
            pending_title = []
            continue
        if tag == "/a":
            if pending_href and pending_title is not None:
                href = pending_href
                title = _clean("".join(pending_title))
                # The generated TOC prefixes each entry with its section number.
                title = re.sub(r"^\d+(?:\.\d+)*\s+", "", title)
                pending_href = None
                pending_title = None
                if (
                    not title
                    or href.startswith(("#", "javascript:", "mailto:"))
                    or "/sp_common/" in href
                ):
                    continue
                if title.lower() == "next" or title.lower() == "previous":
                    continue
                try:
                    url = resolve_topic_url(source, href)
                except KnowledgeError:
                    continue
                key = topic_key_for(source, url)
                if key in seen:
                    continue
                seen.add(key)
                # A nested list item is a child of the nearest still-open
                # ancestor entry at a shallower depth, never of its previous
                # sibling. Pop completed siblings before resolving the parent.
                while stack and stack[-1][0] >= depth:
                    stack.pop()
                parent_key = stack[-1][1] if stack else None
                links.append(
                    TopicLink(
                        topic_key=key,
                        url=url,
                        title=title,
                        depth=depth,
                        order=len(links),
                        parent_key=parent_key,
                    )
                )
                stack.append((depth, key))
            continue
        if token.group("text") and pending_title is not None:
            pending_title.append(token.group("text"))
    if not links:
        raise KnowledgeError("KNOWLEDGE_TOC_NO_TOPICS")
    for link in links:
        link.validate()
    return tuple(links)


def is_same_site(url: str, source: SourceDefinition) -> bool:
    base = urlsplit(source.landing_url)
    candidate = urlsplit(url)
    return candidate.netloc == base.netloc


__all__ = [
    "ParsedPage",
    "build_parsed_topic",
    "is_same_site",
    "parse_help_page",
    "parse_toc",
]
