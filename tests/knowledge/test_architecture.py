from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from construction_pm.knowledge.model import KnowledgeError
from construction_pm.knowledge.sources import (
    INGESTABLE_SOURCES,
    MANDATORY_TOPIC_COVERAGE,
    P6_26_HELP,
    SOURCES,
    get_source,
    mandatory_coverage,
    resolve_topic_url,
    topic_key_for,
)

PACKAGE = Path(__file__).resolve().parents[2] / "src" / "construction_pm" / "knowledge"
MODULES = tuple(sorted(PACKAGE.glob("*.py")))

FORBIDDEN_PROVIDER_TOKENS = (
    "openai",
    "chatgpt",
    "anthropic",
    "claude",
    "ollama",
    "gemini",
    "cohere",
    "sentence-transformers",
    "api_key",
    "api-key",
    "os.environ",
    "getenv",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "flask",
    "django",
    "fastapi",
    "starlette",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "construction_pm.web",
    "construction_pm.visual",
    "apps.",
)
OFFICIAL_HOSTS = {"docs.oracle.com"}


def test_no_external_model_or_provider_dependency() -> None:
    assert MODULES
    for module in MODULES:
        source = module.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_PROVIDER_TOKENS:
            assert token not in source, f"{module.name} references {token}"


def test_no_network_or_shell_client_imports() -> None:
    for module in MODULES:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                for prefix in FORBIDDEN_IMPORT_PREFIXES:
                    assert not name.startswith(prefix), f"{module.name} imports {name}"


def test_only_official_documentation_urls_appear() -> None:
    pattern = re.compile(r"https://([A-Za-z0-9._-]+)")
    for module in MODULES:
        for host in pattern.findall(module.read_text(encoding="utf-8")):
            assert host in OFFICIAL_HOSTS, f"{module.name} cites {host}"


def test_user_facing_assistant_text_has_no_third_party_branding() -> None:
    source = (PACKAGE / "assistant.py").read_text(encoding="utf-8").lower()
    for brand in ("oracle", "primavera", "p6"):
        assert brand not in source


def test_official_source_registry_is_complete() -> None:
    assert len(SOURCES) == 5
    assert len({source.source_id for source in SOURCES}) == 5
    assert len(INGESTABLE_SOURCES) == 3
    for source in SOURCES:
        source.validate()
        assert source.landing_url.startswith("https://docs.oracle.com/")
        assert source.release == "26"
    assert get_source("p6-26-help").toc_url.endswith("/pro-help/toc.htm")
    with pytest.raises(KnowledgeError):
        get_source("unknown-source")


def test_mandatory_coverage_reports_every_required_area() -> None:
    assert len(MANDATORY_TOPIC_COVERAGE) == 31
    report = mandatory_coverage(
        ["Create a Project", "Working with EPS", "Reports", "Activity Table"]
    )
    assert len(report) == 31
    covered = {item["area"] for item in report if item["covered"]}
    assert {"Creating Projects", "Working with EPS", "Reports", "Activity Table"} <= covered
    assert any(not item["covered"] for item in report)


def test_topic_keys_are_stable_and_source_relative() -> None:
    base = P6_26_HELP.toc_url.rsplit("/", 1)[0] + "/"
    absolute = base + "create-project.html"
    assert topic_key_for(P6_26_HELP, absolute) == "create-project.html"
    assert topic_key_for(P6_26_HELP, "create-project.html") == "create-project.html"
    assert topic_key_for(P6_26_HELP, absolute + "#section") == "create-project.html"
    with pytest.raises(KnowledgeError):
        topic_key_for(P6_26_HELP, "http://docs.oracle.com/page.html")


def test_topic_url_resolution_is_https_and_fragment_free() -> None:
    resolved = resolve_topic_url(P6_26_HELP, "nested/page.html#anchor")
    assert resolved.startswith("https://docs.oracle.com/")
    assert resolved.endswith("/pro-help/nested/page.html")
