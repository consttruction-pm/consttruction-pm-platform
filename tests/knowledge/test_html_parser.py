from __future__ import annotations

import pytest

from construction_pm.knowledge.html import build_parsed_topic, parse_help_page, parse_toc
from construction_pm.knowledge.model import KnowledgeError
from construction_pm.knowledge.sources import P6_26_HELP

PAGE_URL = (
    "https://docs.oracle.com/en/industries/construction-engineering/"
    "primavera-p6-professional/26/pro-help/create-project.html"
)

MODERN_PAGE = """
<html><head><title>Create a Project</title></head><body>
<div id="breadcrumb"><a href="../../index.html">Home</a> &gt;
<a href="../projects.html">Projects</a></div>
<article>
  <h1>Create a Project</h1>
  <p>You can create a project to organize activities and resources.</p>
  <h2>Before You Begin</h2>
  <p>You need a calendar and an EPS node before you start.</p>
  <h2>Procedure</h2>
  <ol>
    <li>Choose Project, then Create.</li>
    <li>Enter the project name and unique project ID.</li>
  </ol>
  <p>Note: The project ID must be unique.</p>
  <table>
    <tr><th>Field</th><th>Value</th></tr>
    <tr><td>Name</td><td>Required</td></tr>
  </table>
  <p>Last Published Monday, January 1, 2024</p>
  <a href="create-project-next.html">Next</a>
</article>
</body></html>
"""


def test_parse_modern_article_page() -> None:
    page = parse_help_page(MODERN_PAGE, url=PAGE_URL)

    assert page.title == "Create a Project"
    assert page.breadcrumb == ("Home", "Projects")
    kinds = [block.kind for block in page.blocks]
    assert "heading" in kinds
    assert kinds.count("step") == 2
    assert "table" in kinds
    assert any(block.kind == "note" for block in page.blocks)
    assert all("Last Published" not in block.text for block in page.blocks)
    assert any(block.text == "Field | Value" for block in page.blocks)
    assert PAGE_URL.rsplit("/", 1)[0] + "/create-project-next.html" in page.links


def test_build_parsed_topic_extracts_steps_and_provenance() -> None:
    page = parse_help_page(MODERN_PAGE, url=PAGE_URL)
    known = {
        PAGE_URL,
        PAGE_URL.rsplit("/", 1)[0] + "/create-project-next.html",
        PAGE_URL.rsplit("/", 1)[0] + "/other.html",
    }
    topic = build_parsed_topic(
        page, source=P6_26_HELP, url=PAGE_URL, known_topic_urls=known
    )

    assert topic.topic_key == "create-project.html"
    assert topic.source_id == "p6-26-help"
    assert topic.steps == (
        "Choose Project, then Create.",
        "Enter the project name and unique project ID.",
    )
    assert any("calendar and an EPS node" in item for item in topic.prerequisites)
    assert any("must be unique" in item for item in topic.warnings)
    assert topic.related == ("create-project-next.html",)
    assert topic.parent_key is None
    assert len(topic.content_hash) == 64
    topic.validate()


def test_related_links_are_limited_to_the_same_source() -> None:
    page = parse_help_page(MODERN_PAGE, url=PAGE_URL)
    topic = build_parsed_topic(
        page,
        source=P6_26_HELP,
        url=PAGE_URL,
        known_topic_urls={PAGE_URL, "https://example.invalid/elsewhere.html"},
    )
    assert topic.related == ()


def test_legacy_page_without_article_is_parsed() -> None:
    page = parse_help_page(
        "<html><head><title>Legacy Topic</title></head><body>"
        '<h1 class="topicHeading">Legacy Topic</h1>'
        "<p>Open the project window.</p>"
        "<ul><li>Select the project.</li></ul>"
        "</body></html>",
        url=PAGE_URL,
    )
    assert page.title == "Legacy Topic"
    assert [block.kind for block in page.blocks] == [
        "heading",
        "paragraph",
        "bullet",
    ]


def test_navigation_boilerplate_is_dropped() -> None:
    page = parse_help_page(
        "<html><body><article>"
        "<h1>Working with Projects</h1>"
        "<p>Projects organize your schedule.</p>"
        "<p>Copyright &copy; 2024 Oracle</p>"
        "<p>JavaScript must be enabled to view this page.</p>"
        "<p>Previous</p>"
        "<p>Next</p>"
        "</article></body></html>",
        url=PAGE_URL,
    )
    texts = [block.text for block in page.blocks]
    assert texts == ["Working with Projects", "Projects organize your schedule."]


def test_missing_title_and_empty_html_are_rejected() -> None:
    with pytest.raises(KnowledgeError):
        parse_help_page("<html><body><p>No heading</p></body></html>", url=PAGE_URL)
    with pytest.raises(KnowledgeError):
        parse_help_page("<html></html>", url=PAGE_URL)


def test_chapter_ordinal_span_is_not_part_of_the_title() -> None:
    page = parse_help_page(
        '<html><head><title>Welcome</title></head><body><article>'
        '<h2><span class="enumeration_chapter">1 </span>Welcome</h2>'
        "<p>This chapter introduces the product.</p>"
        "</article></body></html>",
        url=PAGE_URL,
    )
    assert page.title == "Welcome"
    assert page.headings == ((2, "Welcome"),)


def test_subhead_paragraphs_become_section_headings() -> None:
    page = parse_help_page(
        "<html><head><title>Scheduling</title></head><body><article>"
        "<h2>Scheduling</h2>"
        '<p class="subhead1">Calculating a schedule</p>'
        "<p>The schedule is calculated in a forward and backward pass.</p>"
        '<p class="subhead2">Automatic scheduling</p>'
        "<p>Automatic scheduling recalculates after changes.</p>"
        "</article></body></html>",
        url=PAGE_URL,
    )
    assert page.headings == (
        (2, "Scheduling"),
        (3, "Calculating a schedule"),
        (4, "Automatic scheduling"),
    )
    kinds = [(block.kind, block.level) for block in page.blocks]
    assert ("heading", 3) in kinds
    assert ("heading", 4) in kinds
    assert page.blocks[2].section == "Calculating a schedule"


def test_docinfo_heading_is_ignored_and_title_tag_is_used() -> None:
    page = parse_help_page(
        "<html><head><title>Primavera P6 Professional Help</title></head><body><article>"
        '<h2 class="docinfo">Primavera P6 Professional</h2>'
        '<p class="booktitle">Help</p>'
        "</article></body></html>",
        url=PAGE_URL,
    )
    assert page.title == "Primavera P6 Professional Help"
    assert page.headings == ()
    assert [block.text for block in page.blocks] == ["Help"]


def test_toc_title_override_is_used_as_the_topic_title() -> None:
    page = parse_help_page(
        "<html><head><title>Cover</title></head><body><article>"
        '<h2 class="docinfo">Primavera P6 Professional</h2>'
        "<p>Title and Copyright Information</p>"
        "</article></body></html>",
        url=PAGE_URL,
    )
    topic = build_parsed_topic(
        page,
        source=P6_26_HELP,
        url=PAGE_URL,
        title_override="Title and Copyright Information",
    )
    assert topic.title == "Title and Copyright Information"


def test_stub_page_records_that_no_body_content_was_extracted() -> None:
    page = parse_help_page(
        "<html><head><title>Linking Activities</title></head><body><article>"
        "<h2>Linking Activities</h2><p></p>"
        "</article></body></html>",
        url=PAGE_URL,
    )
    topic = build_parsed_topic(page, source=P6_26_HELP, url=PAGE_URL)
    assert any("no body content" in item for item in topic.limitations)
    assert topic.steps == ()


TOC_HTML = """
<article>
<ul>
  <li><a href="a.html">Alpha</a>
    <ul>
      <li><a href="a1.html">Alpha One</a></li>
      <li><a href="a2.html">Alpha Two</a></li>
    </ul>
  </li>
  <li><a href="b.html">Beta</a></li>
  <li><a href="a.html">Alpha Duplicate</a></li>
  <li><a href="/sp_common/skip.html">Skip</a></li>
  <li><a href="mailto:help@example.com">Mail</a></li>
</ul>
</article>
"""


def test_parse_toc_assigns_nearest_ancestor_parent() -> None:
    links = parse_toc(TOC_HTML, source=P6_26_HELP, toc_url=P6_26_HELP.toc_url or "")

    keys = [link.topic_key for link in links]
    assert keys == ["a.html", "a1.html", "a2.html", "b.html"]
    by_key = {link.topic_key: link for link in links}
    assert by_key["a.html"].depth == 1
    assert by_key["a.html"].parent_key is None
    assert by_key["a1.html"].depth == 2
    assert by_key["a1.html"].parent_key == "a.html"
    assert by_key["a2.html"].parent_key == "a.html"
    assert by_key["b.html"].parent_key is None
    assert [link.order for link in links] == [0, 1, 2, 3]


def test_parse_toc_requires_topics() -> None:
    with pytest.raises(KnowledgeError):
        parse_toc("<html><body><p>empty</p></body></html>", source=P6_26_HELP, toc_url="")
