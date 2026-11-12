"""Resumable Version 26 HTML Help ingestion pipeline.

The pipeline discovers the official table of contents, fetches each topic,
parses it, validates it and converts it into a draft Knowledge Card. It is
idempotent, restartable and never reports a page as extracted unless the bytes
were fetched, parsed, validated and stored.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterable, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .cards import build_card
from .html import build_parsed_topic, parse_help_page, parse_toc
from .model import (
    TERMINAL_TOPIC_STATUSES,
    CardStatus,
    KnowledgeCard,
    KnowledgeError,
    SourceDefinition,
    SourceKind,
    iso,
    sha256_hex,
    utc_now,
)
from .sources import (
    INGESTABLE_SOURCES,
    mandatory_coverage,
)
from .store import KnowledgeStore

MAX_PAGE_BYTES = 4_000_000
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 2


def _card_signature(card: KnowledgeCard) -> tuple[object, ...]:
    """Content identity for cross-source de-duplication.

    Two cards are the same topic only when every substantive content field
    matches: title, purpose and the complete procedure/evidence lists. The
    source URL, release and breadcrumb are provenance context and are excluded
    because the same page appears under more than one official root.

    Page filename and card type are deliberately *not* part of the signature.
    Filenames differ between roots for the same topic, and the card type is a
    classification that changes when the page is edited; either one previously
    produced "merges" of pages that merely shared a heading, discarding unique
    body content. Where nothing distinctive matches, the topics stay separate.
    """

    normalize = lambda value: " ".join(str(value).split())
    return (
        normalize(card.title),
        normalize(card.purpose),
        tuple(normalize(step) for step in card.steps),
        tuple(normalize(item) for item in card.prerequisites),
        tuple(normalize(item) for item in card.inputs),
        tuple(normalize(item) for item in card.outputs),
        tuple(normalize(item) for item in card.warnings),
        tuple(normalize(item) for item in card.limitations),
    )


_USER_AGENT = "CUBI-Knowledge-Ingestor/1.0 (internal engineering documentation index)"


class IngestionError(KnowledgeError):
    """Raised when the ingestion pipeline cannot start or persist a step."""


@dataclass(frozen=True)
class FetchResult:
    status: int
    body: bytes | None
    content_type: str | None = None
    error: str | None = None


class Fetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


class UrllibFetcher:
    """Bounded HTTPS fetcher for the official documentation hosts."""

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = MAX_PAGE_BYTES,
        allowed_hosts: Sequence[str] = (
            "docs.oracle.com",
            "www.oracle.com",
            "oracle.com",
        ),
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.allowed_hosts = tuple(allowed_hosts)

    def fetch(self, url: str) -> FetchResult:
        if not url.startswith("https://"):
            return FetchResult(0, None, error="KNOWLEDGE_FETCH_REQUIRES_HTTPS")
        host = url.split("/", 3)[2].split(":", 1)[0].lower()
        if not any(host == allowed or host.endswith("." + allowed) for allowed in self.allowed_hosts):
            return FetchResult(0, None, error="KNOWLEDGE_FETCH_HOST_NOT_ALLOWED")
        request = Request(
            url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - host allowlist above
                status = int(response.status)
                content_type = response.headers.get("Content-Type", "")
                raw = response.read(self.max_bytes + 1)
        except HTTPError as exc:
            return FetchResult(int(exc.code), None, error=f"KNOWLEDGE_HTTP_{exc.code}")
        except (URLError, TimeoutError, OSError):
            return FetchResult(0, None, error="KNOWLEDGE_FETCH_UNAVAILABLE")
        if len(raw) > self.max_bytes:
            return FetchResult(status, None, error="KNOWLEDGE_PAGE_TOO_LARGE")
        if status != 200:
            return FetchResult(status, None, error=f"KNOWLEDGE_HTTP_{status}")
        if content_type and "html" not in content_type.lower() and "text" not in content_type.lower():
            return FetchResult(status, None, error="KNOWLEDGE_PAGE_NOT_HTML")
        return FetchResult(status, raw, content_type=content_type)


@dataclass(frozen=True)
class IngestionReport:
    source_id: str
    discovered: int
    newly_discovered: int
    processed: int
    converted: int
    skipped: int
    failed: int
    failures: tuple[dict[str, str], ...]
    coverage: tuple[dict[str, object], ...]
    started_at: str
    finished_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "discovered": self.discovered,
            "newly_discovered": self.newly_discovered,
            "processed": self.processed,
            "converted": self.converted,
            "skipped": self.skipped,
            "failed": self.failed,
            "failures": list(self.failures),
            "coverage": list(self.coverage),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


@dataclass
class IngestionPipeline:
    """Discover, fetch, parse, validate and convert one official source."""

    store: KnowledgeStore
    fetcher: Fetcher = field(default_factory=UrllibFetcher)
    clock: Callable[[], datetime] = utc_now
    delay_seconds: float = 0.0
    max_retries: int = MAX_RETRIES
    # Pages are parsed and stored on one thread; only HTTP fetches run in
    # parallel. Higher values shorten a full documentation ingest without
    # weakening provenance, idempotency or write ordering.
    fetch_workers: int = 1
    # The same topic is published under more than one official root (for
    # example client_help and the user guide). Identical content is stored once
    # per source topic, but only one card is created so duplicates are merged
    # while every source topic and URL remains recorded.
    _content_index: dict[tuple[object, ...], str] | None = field(
        default=None, init=False, repr=False
    )

    def _audit(
        self,
        *,
        source_id: str,
        action: str,
        outcome: str,
        detail: Mapping[str, object],
    ) -> None:
        self.store.append_audit(
            tenant_id=None,
            project_id=None,
            actor_id="knowledge-ingestor",
            action=action,
            entity_kind="knowledge_source",
            entity_id=source_id,
            outcome=outcome,
            occurred_at=iso(self.clock()),
            detail=detail,
        )

    def _card_index(self) -> dict[tuple[object, ...], str]:
        if self._content_index is None:
            index: dict[tuple[object, ...], str] = {}
            for card in self.store.list_cards(
                scope="central",
                publication_statuses=[
                    CardStatus.DRAFT.value,
                    CardStatus.VALIDATED.value,
                    CardStatus.PUBLISHED.value,
                ],
            ):
                index.setdefault(_card_signature(card), card.card_id)
            self._content_index = index
        return self._content_index

    # -- discovery -------------------------------------------------------
    def discover(self, source: SourceDefinition) -> tuple[int, int]:
        if source.toc_url is None:
            raise IngestionError("KNOWLEDGE_SOURCE_HAS_NO_TOC")
        result = self.fetcher.fetch(source.toc_url)
        if result.error or not result.body:
            self._audit(
                source_id=source.source_id,
                action="toc_fetch_failed",
                outcome="failed",
                detail={"error": result.error or "KNOWLEDGE_TOC_EMPTY"},
            )
            raise IngestionError(result.error or "KNOWLEDGE_TOC_EMPTY")
        html = result.body.decode("utf-8", errors="replace")
        links = parse_toc(html, source=source, toc_url=source.toc_url)
        now = iso(self.clock())
        inserted = 0
        for link in links:
            if self.store.upsert_discovered_topic(source.source_id, link, discovered_at=now):
                inserted += 1
        self.store.upsert_source(
            source,
            status="discovered",
            content_hash=sha256_hex(html),
            retrieved_at=now,
            metadata={
                "topic_count": len(links),
                "toc_url": source.toc_url,
                "discovered_at": now,
            },
        )
        self._audit(
            source_id=source.source_id,
            action="discover",
            outcome="succeeded",
            detail={"topics": len(links), "new": inserted},
        )
        return len(links), inserted

    # -- processing ------------------------------------------------------
    def _work_queue(
        self, source: SourceDefinition, *, force: bool, max_pages: int | None
    ) -> tuple[dict[str, object], ...]:
        statuses = (
            None
            if force
            else ["pending", "downloaded", "parsed", "validated", "failed"]
        )
        topics = list(self.store.list_topics(source_id=source.source_id, statuses=statuses))
        if not force:
            # A failed page is retried only while its retry budget remains.
            topics = [
                topic
                for topic in topics
                if int(topic.get("retry_count", 0)) <= self.max_retries
            ]
        if max_pages is not None:
            topics = topics[:max_pages]
        return tuple(topics)

    # -- per-topic processing --------------------------------------------
    def _apply_topic(
        self,
        source: SourceDefinition,
        topic: Mapping[str, object],
        result: FetchResult,
        *,
        all_links: set[str],
        force: bool,
    ) -> tuple[str, str | None, bool]:
        """Persist one fetched topic and return ``(status, error, card_skipped)``."""

        topic_id = str(topic["topic_id"])
        topic_key = str(topic["topic_key"])
        url = str(topic["url"])
        if result.error or result.body is None:
            error_code = result.error or "KNOWLEDGE_FETCH_UNAVAILABLE"
            self.store.mark_topic_failure(
                topic_id, error_code, occurred_at=iso(self.clock())
            )
            self._audit(
                source_id=source.source_id,
                action="topic_fetch_failed",
                outcome="failed",
                detail={"topic_key": topic_key, "error": error_code},
            )
            return "failed", error_code, False
        try:
            html = result.body.decode("utf-8", errors="replace")
            page = parse_help_page(html, url=url)
            parsed = build_parsed_topic(
                page,
                source=source,
                url=url,
                parent_key=None if topic["parent_key"] is None else str(topic["parent_key"]),
                known_topic_urls=all_links,
                title_override=str(topic["title"]) if topic.get("title") else None,
            )
            card = build_card(
                parsed,
                source_version=source.release,
                extracted_at=self.clock(),
            )
        except KnowledgeError as exc:
            code = str(exc) or "KNOWLEDGE_PARSE_FAILED"
            self.store.mark_topic_failure(
                topic_id, code, occurred_at=iso(self.clock())
            )
            self._audit(
                source_id=source.source_id,
                action="topic_parse_failed",
                outcome="failed",
                detail={"topic_key": topic_key, "error": code},
            )
            return "failed", code, False
        existing_card = self.store.get_card(card.card_id)
        index = self._card_index()
        signature = _card_signature(card)
        canonical = index.get(signature)
        if canonical is not None and canonical != card.card_id:
            # The same official topic text is already in the knowledge base
            # under another source root. Keep the canonical card, record this
            # topic as converted and preserve the duplicate provenance.
            self.store.save_parsed_topic(
                parsed,
                status="converted",
                http_status=result.status,
                occurred_at=iso(self.clock()),
            )
            self._audit(
                source_id=source.source_id,
                action="topic_merged",
                outcome="succeeded",
                detail={
                    "topic_key": topic_key,
                    "duplicate_topic_id": parsed.topic_id,
                    "duplicate_url": parsed.url,
                    "canonical_card_id": canonical,
                    "duplicate_card_id": card.card_id,
                },
            )
            return "converted", None, False
        protected = (
            existing_card is not None
            and existing_card.publication_status is not CardStatus.DRAFT
        )
        if protected:
            # Re-ingestion must never un-publish a reviewed card. When the
            # source text changed, keep the published version and record the
            # pending regeneration for a human to review and republish.
            if existing_card.content_hash != card.content_hash:
                self.store.record_card_event(
                    card.card_id,
                    action="regeneration_blocked",
                    actor_id="knowledge-ingestor",
                    occurred_at=iso(self.clock()),
                    detail={
                        "content_hash": card.content_hash,
                        "stored_content_hash": existing_card.content_hash,
                        "publication_status": existing_card.publication_status.value,
                    },
                )
                self._audit(
                    source_id=source.source_id,
                    action="topic_regeneration_blocked",
                    outcome="succeeded",
                    detail={
                        "topic_key": topic_key,
                        "card_id": card.card_id,
                        "publication_status": existing_card.publication_status.value,
                    },
                )
            self.store.save_parsed_topic(
                parsed,
                status="converted",
                http_status=result.status,
                occurred_at=iso(self.clock()),
            )
            return "converted", None, True
        unchanged = (
            existing_card is not None
            and existing_card.content_hash == card.content_hash
            and not force
        )
        if not unchanged:
            self.store.save_card(card)
            if existing_card is not None:
                self.store.record_card_event(
                    card.card_id,
                    action="regenerated",
                    actor_id="knowledge-ingestor",
                    occurred_at=iso(self.clock()),
                    detail={"content_hash": card.content_hash},
                )
        index[signature] = card.card_id
        self.store.save_parsed_topic(
            parsed,
            status="converted",
            http_status=result.status,
            occurred_at=iso(self.clock()),
        )
        return "converted", None, unchanged

    def run(
        self,
        source: SourceDefinition,
        *,
        max_pages: int | None = None,
        force: bool = False,
        progress: Callable[[dict[str, object]], None] | None = None,
    ) -> IngestionReport:
        if source.kind not in {SourceKind.HELP, SourceKind.USER_GUIDE, SourceKind.HTML_HELP}:
            raise IngestionError("KNOWLEDGE_SOURCE_NOT_INGESTABLE")
        started = iso(self.clock())
        discovered, inserted = self.discover(source)
        queue = self._work_queue(source, force=force, max_pages=max_pages)
        all_links = {
            str(topic["url"]) for topic in self.store.list_topics(source_id=source.source_id)
        }
        converted = 0
        failed = 0
        skipped = 0
        processed = 0
        failures: list[dict[str, str]] = []
        workers = max(1, int(self.fetch_workers))
        batch_size = max(1, workers * 4)
        for offset in range(0, len(queue), batch_size):
            batch = queue[offset : offset + batch_size]
            if workers > 1:
                if self.delay_seconds and offset:
                    time.sleep(self.delay_seconds)
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    results = list(
                        pool.map(lambda item: self.fetcher.fetch(str(item["url"])), batch)
                    )
            else:
                results = [self.fetcher.fetch(str(topic["url"])) for topic in batch]
            for topic, result in zip(batch, results):
                processed += 1
                status, error, card_skipped = self._apply_topic(
                    source,
                    topic,
                    result,
                    all_links=all_links,
                    force=force,
                )
                if status == "failed":
                    failed += 1
                    failures.append(
                        {"topic_key": str(topic["topic_key"]), "error": error or "KNOWLEDGE_PARSE_FAILED"}
                    )
                else:
                    converted += 1
                    if card_skipped:
                        skipped += 1
                if progress is not None:
                    progress(
                        {
                            "processed": processed,
                            "converted": converted,
                            "failed": failed,
                            "topic_key": topic["topic_key"],
                            "status": status,
                        }
                    )
                if workers == 1 and self.delay_seconds:
                    time.sleep(self.delay_seconds)
        counts = self.store.topic_counts(source.source_id)
        completed = counts.get("converted", 0) + counts.get("published", 0)
        outstanding = counts.get("total", 0) - completed
        source_status = (
            "converted" if outstanding == 0 else ("partial" if completed else "failed")
        )
        record = self.store.get_source(source.source_id) or {}
        metadata = dict(record.get("metadata") or {})
        metadata.update({"ingested_at": iso(self.clock()), "counts": counts})
        self.store.upsert_source(
            source,
            status=source_status,
            content_hash=(
                str(record["content_hash"]) if record.get("content_hash") else None
            ),
            retrieved_at=(
                str(record["retrieved_at"]) if record.get("retrieved_at") else None
            ),
            metadata=metadata,
        )
        report = IngestionReport(
            source_id=source.source_id,
            discovered=discovered,
            newly_discovered=inserted,
            processed=processed,
            converted=converted,
            skipped=skipped,
            failed=failed,
            failures=tuple(failures),
            coverage=mandatory_coverage(self.store.topic_titles(source.source_id)),
            started_at=started,
            finished_at=iso(self.clock()),
        )
        self._audit(
            source_id=source.source_id,
            action="ingest_run",
            outcome="succeeded" if failed == 0 and outstanding == 0 else "partial",
            detail={
                "processed": processed,
                "converted": converted,
                "outstanding": outstanding,
                "failed": failed,
                "skipped": skipped,
            },
        )
        return report

    # -- coverage --------------------------------------------------------
    def coverage_report(self) -> dict[str, object]:
        sources: list[dict[str, object]] = []
        for source in INGESTABLE_SOURCES:
            record = self.store.get_source(source.source_id)
            counts = self.store.topic_counts(source.source_id)
            topics = self.store.list_topics(source_id=source.source_id)
            failures = [
                {
                    "topic_key": topic["topic_key"],
                    "title": topic["title"],
                    "error": topic["error_code"],
                }
                for topic in topics
                if topic["status"] == "failed"
            ]
            pending = [
                topic["topic_key"]
                for topic in topics
                if topic["status"] not in TERMINAL_TOPIC_STATUSES
            ]
            sources.append(
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "status": None if record is None else record["status"],
                    "counts": counts,
                    "unconverted_topics": pending[:200],
                    "failures": failures[:200],
                    "mandatory_areas": list(
                        mandatory_coverage(self.store.topic_titles(source.source_id))
                    ),
                }
            )
        return {
            "contract_version": "cubi-knowledge-coverage.v1",
            "sources": sources,
            "card_counts": _card_counts(self.store),
        }


def _card_counts(store: KnowledgeStore) -> dict[str, int]:
    counts = {"draft": 0, "validated": 0, "published": 0, "rejected": 0, "retired": 0}
    cards = store.list_cards()
    for card in cards:
        key = card.publication_status.value
        counts[key] = counts.get(key, 0) + 1
    counts["total"] = len(cards)
    return counts


def ingest_all(
    store: KnowledgeStore,
    *,
    sources: Iterable[SourceDefinition] = INGESTABLE_SOURCES,
    max_pages_per_source: int | None = None,
    force: bool = False,
    fetcher: Fetcher | None = None,
    progress: Callable[[dict[str, object]], None] | None = None,
) -> tuple[IngestionReport, ...]:
    pipeline = IngestionPipeline(store=store, **({} if fetcher is None else {"fetcher": fetcher}))
    reports: list[IngestionReport] = []
    for source in sources:
        reports.append(
            pipeline.run(
                source,
                max_pages=max_pages_per_source,
                force=force,
                progress=progress,
            )
        )
    return tuple(reports)


__all__ = [
    "FetchResult",
    "Fetcher",
    "IngestionError",
    "IngestionPipeline",
    "IngestionReport",
    "UrllibFetcher",
    "ingest_all",
]
