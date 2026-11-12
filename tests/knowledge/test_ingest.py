from __future__ import annotations

import pytest

from construction_pm.knowledge.ingest import (
    FetchResult,
    IngestionError,
    IngestionPipeline,
    UrllibFetcher,
    ingest_all,
)
from construction_pm.knowledge.sources import P6_26_BOOKS, P6_26_HELP

TOC_URL = P6_26_HELP.toc_url
BASE = TOC_URL.rsplit("/", 1)[0] + "/"

TOC_HTML = """
<article><ul>
  <li><a href="create-project.html">Create a Project</a></li>
  <li><a href="schedule.html">Schedule a Project</a></li>
</ul></article>
"""

CREATE_HTML = """
<html><head><title>Create a Project</title></head><body><article>
<h1>Create a Project</h1>
<p>You can create a project to organize activities.</p>
<h2>Procedure</h2>
<ol><li>Choose Project, then Create.</li><li>Enter the project name.</li></ol>
</article></body></html>
"""

SCHEDULE_HTML = """
<html><head><title>Schedule a Project</title></head><body><article>
<h1>Schedule a Project</h1>
<p>You can schedule a project after activities are linked.</p>
<p>Note: Scheduling cannot run when a loop exists.</p>
</article></body></html>
"""


class FakeFetcher:
    def __init__(self, pages: dict[str, str], failures: dict[str, str] | None = None) -> None:
        self.pages = dict(pages)
        self.failures = dict(failures or {})
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        if url in self.failures:
            return FetchResult(0, None, error=self.failures[url])
        body = self.pages.get(url)
        if body is None:
            return FetchResult(404, None, error="KNOWLEDGE_HTTP_404")
        return FetchResult(200, body.encode("utf-8"), content_type="text/html")


def pages() -> dict[str, str]:
    return {
        TOC_URL: TOC_HTML,
        BASE + "create-project.html": CREATE_HTML,
        BASE + "schedule.html": SCHEDULE_HTML,
    }


def test_pipeline_converts_every_discovered_topic(store, clock) -> None:
    fetcher = FakeFetcher(pages())
    pipeline = IngestionPipeline(store=store, fetcher=fetcher, clock=clock)

    report = pipeline.run(P6_26_HELP)

    assert report.discovered == 2
    assert report.newly_discovered == 2
    assert report.processed == 2
    assert report.converted == 2
    assert report.failed == 0
    assert report.failures == ()
    assert store.get_source("p6-26-help")["status"] == "converted"
    topics = store.list_topics(source_id="p6-26-help")
    assert {topic["status"] for topic in topics} == {"converted"}
    assert all(topic["http_status"] == 200 for topic in topics)
    cards = store.list_cards()
    assert len(cards) == 2
    assert {card.publication_status.value for card in cards} == {"draft"}
    covered = {item["area"]: item["covered"] for item in report.coverage}
    assert covered["Creating Projects"] is True
    assert covered["Scheduling Projects"] is True
    assert covered["Reports"] is False


def test_parallel_fetch_keeps_order_and_results(store, clock) -> None:
    fetcher = FakeFetcher(pages())
    pipeline = IngestionPipeline(
        store=store, fetcher=fetcher, clock=clock, fetch_workers=4
    )

    report = pipeline.run(P6_26_HELP)

    assert report.discovered == 2
    assert report.converted == 2
    assert report.failed == 0
    topics = store.list_topics(source_id="p6-26-help")
    assert [topic["topic_key"] for topic in topics] == [
        "create-project.html",
        "schedule.html",
    ]
    assert all(topic["status"] == "converted" for topic in topics)


def test_second_run_is_idempotent(store, clock) -> None:
    fetcher = FakeFetcher(pages())
    pipeline = IngestionPipeline(store=store, fetcher=fetcher, clock=clock)

    first = pipeline.run(P6_26_HELP)
    second = pipeline.run(P6_26_HELP)

    assert first.converted == 2
    assert second.newly_discovered == 0
    assert second.processed == 0
    assert second.converted == 0
    assert len(store.list_cards()) == 2


def test_failed_page_is_retried_on_the_next_run(store, clock) -> None:
    fetcher = FakeFetcher(
        pages(), failures={BASE + "schedule.html": "KNOWLEDGE_HTTP_500"}
    )
    pipeline = IngestionPipeline(store=store, fetcher=fetcher, clock=clock)

    first = pipeline.run(P6_26_HELP)
    assert first.failed == 1
    assert first.converted == 1
    failed_topic = store.get_topic_by_key("p6-26-help", "schedule.html")
    assert failed_topic["status"] == "failed"
    assert failed_topic["retry_count"] == 1

    fetcher.failures.clear()
    second = pipeline.run(P6_26_HELP)
    assert second.processed == 1
    assert second.converted == 1
    assert store.get_topic_by_key("p6-26-help", "schedule.html")["status"] == "converted"


def test_partial_ingest_never_reports_success(store, clock) -> None:
    """C: a run with a failed page is partial, never success."""

    fetcher = FakeFetcher(
        pages(), failures={BASE + "schedule.html": "KNOWLEDGE_HTTP_500"}
    )
    pipeline = IngestionPipeline(store=store, fetcher=fetcher, clock=clock)

    report = pipeline.run(P6_26_HELP)

    assert report.discovered == 2
    assert report.converted == 1
    assert report.failed == 1
    assert report.failures == (
        {"topic_key": "schedule.html", "error": "KNOWLEDGE_HTTP_500"},
    )
    assert store.get_source(P6_26_HELP.source_id)["status"] == "partial"
    outcomes = [
        row["outcome"]
        for row in store.list_audit(tenant_id=None, limit=50)
        if row["action"] == "ingest_run"
    ]
    assert outcomes == ["partial"]


def test_max_pages_limits_the_queue_without_losing_discovery(store, clock) -> None:
    pipeline = IngestionPipeline(store=store, fetcher=FakeFetcher(pages()), clock=clock)

    report = pipeline.run(P6_26_HELP, max_pages=1)

    assert report.discovered == 2
    assert report.processed == 1
    assert report.converted == 1
    statuses = {
        topic["topic_key"]: topic["status"]
        for topic in store.list_topics(source_id="p6-26-help")
    }
    assert statuses == {"create-project.html": "converted", "schedule.html": "pending"}


def test_changed_content_is_snapshotted_on_force(store, clock) -> None:
    fetcher = FakeFetcher(pages())
    pipeline = IngestionPipeline(store=store, fetcher=fetcher, clock=clock)
    pipeline.run(P6_26_HELP)

    fetcher.pages[BASE + "create-project.html"] = CREATE_HTML.replace(
        "organize activities", "organize activities, resources and costs"
    )
    report = pipeline.run(P6_26_HELP, force=True)

    assert report.converted == 2
    topic = store.get_topic_by_key("p6-26-help", "create-project.html")
    snapshots = store.topic_snapshots(str(topic["topic_id"]))
    assert len(snapshots) == 1
    assert snapshots[0]["content_hash"] != topic["content_hash"]


def test_force_reingestion_never_unpublishes_a_reviewed_card(store, clock) -> None:
    from construction_pm.knowledge.cards import publish_card, review_card
    from construction_pm.knowledge.model import CardStatus

    fetcher = FakeFetcher(pages())
    pipeline = IngestionPipeline(store=store, fetcher=fetcher, clock=clock)
    pipeline.run(P6_26_HELP)
    draft = next(
        card for card in store.list_cards() if card.title == "Create a Project"
    )
    published = publish_card(
        review_card(draft, reviewer="reviewer-1"),
        reviewer="reviewer-1",
        published_at=clock.now(),
    )
    store.save_card(published)

    fetcher.pages[BASE + "create-project.html"] = CREATE_HTML.replace(
        "organize activities", "organize activities, resources and costs"
    )
    report = pipeline.run(P6_26_HELP, force=True)

    assert report.converted == 2
    stored = store.get_card(published.card_id)
    assert stored.publication_status is CardStatus.PUBLISHED
    assert stored.reviewer == "reviewer-1"
    assert stored.revision == published.revision
    assert stored.content_hash == published.content_hash
    topic = store.get_topic_by_key("p6-26-help", "create-project.html")
    assert topic["content_hash"] != stored.content_hash
    actions = {row["action"] for row in store.list_audit(tenant_id=None, limit=50)}
    assert "topic_regeneration_blocked" in actions


def test_coverage_report_and_ingest_all(store, clock) -> None:
    pipeline = IngestionPipeline(store=store, fetcher=FakeFetcher(pages()), clock=clock)
    reports = ingest_all(
        store,
        sources=(P6_26_HELP,),
        fetcher=pipeline.fetcher,
        max_pages_per_source=1,
    )

    assert len(reports) == 1
    assert reports[0].converted == 1
    coverage = pipeline.coverage_report()
    assert coverage["contract_version"] == "cubi-knowledge-coverage.v1"
    assert [item["source_id"] for item in coverage["sources"]] == [
        "p6-26-html-help",
        "p6-26-user-guide",
    ]
    assert coverage["card_counts"]["draft"] >= 1
    assert coverage["card_counts"]["published"] == 0


def test_discovery_requires_a_table_of_contents(store, clock) -> None:
    pipeline = IngestionPipeline(store=store, fetcher=FakeFetcher({}), clock=clock)
    with pytest.raises(IngestionError):
        pipeline.run(P6_26_BOOKS)


def test_urllib_fetcher_refuses_non_https_and_foreign_hosts() -> None:
    fetcher = UrllibFetcher()
    assert fetcher.fetch("http://docs.oracle.com/page.html").error == (
        "KNOWLEDGE_FETCH_REQUIRES_HTTPS"
    )
    assert fetcher.fetch("https://example.invalid/page.html").error == (
        "KNOWLEDGE_FETCH_HOST_NOT_ALLOWED"
    )


def test_identical_topics_from_two_official_roots_are_merged(store, clock) -> None:
    from construction_pm.knowledge.model import SourceDefinition, SourceKind

    root_a = "https://docs.example.test/help/toc.htm"
    root_b = "https://docs.example.test/guide/toc.htm"
    source_a = SourceDefinition(
        source_id="test-help",
        title="Help",
        kind=SourceKind.HELP,
        release="26",
        landing_url=root_a,
        toc_url=root_a,
    )
    source_b = SourceDefinition(
        source_id="test-guide",
        title="Guide",
        kind=SourceKind.USER_GUIDE,
        release="26",
        landing_url=root_b,
        toc_url=root_b,
    )
    fetcher = FakeFetcher(
        {
            root_a: TOC_HTML,
            root_b: TOC_HTML,
            "https://docs.example.test/help/create-project.html": CREATE_HTML,
            "https://docs.example.test/help/schedule.html": SCHEDULE_HTML,
            "https://docs.example.test/guide/create-project.html": CREATE_HTML,
            "https://docs.example.test/guide/schedule.html": SCHEDULE_HTML,
        }
    )
    pipeline = IngestionPipeline(store=store, fetcher=fetcher, clock=clock)

    pipeline.run(source_a)
    pipeline.run(source_b)

    topics = store.list_topics(source_id="test-guide")
    assert {topic["status"] for topic in topics} == {"converted"}
    cards = store.list_cards(
        scope="central",
        publication_statuses=["draft", "validated", "published"],
    )
    assert len(cards) == 2
    assert all(card.source_url.startswith(root_a.rsplit("/toc", 1)[0]) for card in cards)
    events = [
        row for row in store.list_audit(tenant_id=None) if row["action"] == "topic_merged"
    ]
    assert len(events) == 2
