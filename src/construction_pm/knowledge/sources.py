"""Official Version 26 reference registry for the CUBI knowledge pipeline.

Only these official locations are authoritative. Source names and URLs are kept
in internal engineering traceability records; nothing here may leak into the
CUBI user interface as third-party branding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlsplit

from .model import KnowledgeError, SourceDefinition, SourceKind

DOCS_HOME = (
    "https://docs.oracle.com/en/industries/construction-engineering/"
    "primavera-p6-professional/26/"
)

P6_26_HELP = SourceDefinition(
    source_id="p6-26-help",
    title="Version 26 Professional Help",
    kind=SourceKind.HELP,
    release="26",
    landing_url=f"{DOCS_HOME}pro-help/index.html",
    toc_url=f"{DOCS_HOME}pro-help/toc.htm",
)

P6_26_USER_GUIDE = SourceDefinition(
    source_id="p6-26-user-guide",
    title="Version 26 Professional User Guide",
    kind=SourceKind.USER_GUIDE,
    release="26",
    landing_url="https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm",
    toc_url="https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm",
)

P6_26_HTML_HELP = SourceDefinition(
    source_id="p6-26-html-help",
    title="Version 26 HTML Help table of contents",
    kind=SourceKind.HTML_HELP,
    release="26",
    landing_url="https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",
    toc_url="https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",
)

P6_26_BOOKS = SourceDefinition(
    source_id="p6-26-books",
    title="Version 26 documentation index",
    kind=SourceKind.DOCUMENT_INDEX,
    release="26",
    landing_url=f"{DOCS_HOME}books.html",
    toc_url=None,
)

P6_26_DOCS_HOME = SourceDefinition(
    source_id="p6-26-docs-home",
    title="Version 26 documentation set",
    kind=SourceKind.DOCUMENTATION_HOME,
    release="26",
    landing_url=DOCS_HOME,
    toc_url=None,
)

SOURCES: tuple[SourceDefinition, ...] = (
    P6_26_HELP,
    P6_26_USER_GUIDE,
    P6_26_HTML_HELP,
    P6_26_BOOKS,
    P6_26_DOCS_HOME,
)

INGESTABLE_SOURCES: tuple[SourceDefinition, ...] = (
    P6_26_HTML_HELP,
    P6_26_USER_GUIDE,
)

MANDATORY_TOPIC_COVERAGE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Workspace Basics", ("workspace basics",)),
    ("Working with Toolbars and Menus", ("working with toolbars", "toolbars and menus")),
    ("Setting User Preferences", ("user preferences", "set user preferences")),
    ("Working with Projects", ("working with projects",)),
    ("Creating Projects", ("create a project", "creating a project", "create project")),
    ("Working with EPS", ("eps",)),
    ("Developing Projects", ("developing projects", "develop a project")),
    ("Work Breakdown Structure", ("work breakdown structure", "wbs")),
    ("Activities", ("activities", "activity")),
    ("Linking Activities with Relationships", ("relationship", "linking activities")),
    ("Calendars", ("calendar",)),
    ("Resources", ("resources", "resource")),
    ("Roles", ("roles", "role")),
    ("Managing Projects", ("managing projects", "manage a project")),
    ("Creating Baselines", ("baseline",)),
    ("Updating Projects", ("update projects", "update a project", "updating projects")),
    ("Scheduling Projects", ("scheduling projects", "schedule a project", "schedule")),
    ("Checking Schedules", ("check schedule", "checking schedules")),
    ("Leveling Resources", ("leveling", "levelling")),
    ("Customizing Activity Layouts", ("customizing activity layouts", "activity layout")),
    ("Activity Table", ("activity table",)),
    ("Gantt Chart", ("gantt",)),
    ("Grouping, Filtering, and Summarizing Data", ("grouping", "filter", "summariz")),
    ("Reports", ("reports", "report")),
    ("Project Management", ("project management", "managing projects")),
    ("Project Codes", ("project code",)),
    ("Activity Codes", ("activity code",)),
    ("User Defined Fields", ("user defined field", "user-defined field", "udf")),
    ("Global Change", ("global change",)),
    ("Earned Value", ("earned value",)),
    ("Project Progress", ("project progress", "progress")),
)


def get_source(source_id: str) -> SourceDefinition:
    for source in SOURCES:
        if source.source_id == source_id:
            return source
    raise KnowledgeError("KNOWLEDGE_SOURCE_UNKNOWN")


def _normalized_path(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        raise KnowledgeError("KNOWLEDGE_TOPIC_URL_INVALID")
    return parts.path


def topic_key_for(source: SourceDefinition, url: str) -> str:
    """Return a stable key that is unique within one source.

    The key is the URL path relative to the source landing directory, so a
    re-run of the pipeline maps the same page to the same record.
    """

    base = source.toc_url or source.landing_url
    if not url.startswith("https://"):
        url = urljoin(base, url)
    page_path = _normalized_path(url)
    base_path = _normalized_path(base)
    base_dir = base_path.rsplit("/", 1)[0] + "/"
    if page_path.startswith(base_dir):
        key = page_path[len(base_dir):]
    else:
        key = page_path.lstrip("/")
    key = key.split("#", 1)[0].split("?", 1)[0]
    if not key:
        raise KnowledgeError("KNOWLEDGE_TOPIC_KEY_INVALID")
    return key


def resolve_topic_url(source: SourceDefinition, href: str) -> str:
    base = source.toc_url or source.landing_url
    resolved = urljoin(base, href)
    if not resolved.startswith("https://"):
        raise KnowledgeError("KNOWLEDGE_TOPIC_URL_INVALID")
    return resolved.split("#", 1)[0]


def mandatory_coverage(topic_titles: Iterable[str]) -> tuple[dict[str, object], ...]:
    """Report which required Version 26 subject areas were actually discovered."""

    normalized = [" ".join(title.lower().split()) for title in topic_titles]
    report: list[dict[str, object]] = []
    for label, needles in MANDATORY_TOPIC_COVERAGE:
        matches = [
            title
            for title in normalized
            if any(needle in title for needle in needles)
        ]
        report.append(
            {
                "area": label,
                "covered": bool(matches),
                "match_count": len(matches),
                "examples": matches[:5],
            }
        )
    return tuple(report)


__all__ = [
    "DOCS_HOME",
    "INGESTABLE_SOURCES",
    "MANDATORY_TOPIC_COVERAGE",
    "P6_26_BOOKS",
    "P6_26_DOCS_HOME",
    "P6_26_HELP",
    "P6_26_HTML_HELP",
    "P6_26_USER_GUIDE",
    "SOURCES",
    "get_source",
    "mandatory_coverage",
    "resolve_topic_url",
    "topic_key_for",
]
