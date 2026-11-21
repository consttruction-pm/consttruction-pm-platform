"""Routing tests for the Vercel workspace entrypoints.

Vercel maps every workspace document onto one Python function. If the original
route is lost, ``/enterprise`` and ``/cubi/*`` silently become the Engineering
shell. These tests pin the resolver and the deployment configuration that feeds
it.
"""

from __future__ import annotations

import json
from pathlib import Path

from construction_pm.deployment.workspace_routes import (
    query_without_rewrite,
    resolve_workspace_path,
)

ROOT = Path(__file__).resolve().parents[1]


def _resolve(path: str = "/api/shell", query: str = "") -> str:
    return resolve_workspace_path({"PATH_INFO": path, "QUERY_STRING": query})


def test_engineering_and_legacy_routes_resolve_without_the_rewrite_query() -> None:
    assert _resolve("/app") == "/app"
    assert _resolve("/app/") == "/app"
    assert _resolve("/enterprise") == "/enterprise"
    assert _resolve("/enterprise/") == "/enterprise"


def test_rewritten_paths_preserve_the_requested_document() -> None:
    assert _resolve("/api/shell", "__path=enterprise") == "/enterprise"
    assert _resolve("/api/shell", "__path=cubi") == "/cubi"
    assert _resolve("/api/shell", "__path=cubi%2Fenterprise%2Fdashboard") == (
        "/cubi/enterprise/dashboard"
    )
    assert _resolve("/api/shell", "__path=ai-workbench") == "/ai-workbench"
    assert _resolve("/api/shell", "__path=ai-workbench&project=p1") == "/ai-workbench"


def test_direct_invocation_keeps_enterprise_and_workbench_paths() -> None:
    assert _resolve("/cubi/enterprise/tasks") == "/cubi/enterprise/tasks"
    assert _resolve("/ai-workbench") == "/ai-workbench"


def test_unknown_or_traversing_paths_fall_back_to_the_engineering_shell() -> None:
    assert _resolve("/api/shell", "__path=anything-else") == "/app"
    assert _resolve("/api/shell", "__path=cubi%2F..%2F..%2Fetc%2Fpasswd") == "/app"
    assert _resolve("/api/shell", "__path=..%2F..%2Fetc") == "/app"
    assert _resolve("/api/shell", "__path=") == "/app"
    assert _resolve("/random") == "/app"


def test_rewrite_marker_is_removed_from_the_user_query() -> None:
    assert query_without_rewrite(
        {"QUERY_STRING": "__path=cubi%2Fenterprise%2Fdashboard&project=alpha&lang=fa"}
    ) == "project=alpha&lang=fa"
    assert query_without_rewrite({"QUERY_STRING": "__path=ai-workbench"}) == ""
    assert query_without_rewrite({"QUERY_STRING": "project=alpha"}) == "project=alpha"


def test_both_entrypoints_share_the_resolver() -> None:
    for entrypoint in (ROOT / "api" / "shell.py", ROOT / "apps" / "web" / "api" / "shell.py"):
        source = entrypoint.read_text(encoding="utf-8")
        assert "resolve_workspace_path" in source, entrypoint
        assert 'PATH_INFO"] = "/app"' not in source, entrypoint


def test_vercel_config_routes_every_workspace_document_to_the_shell() -> None:
    for config_path in (ROOT / "vercel.json", ROOT / "apps" / "web" / "vercel.json"):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        rewrites = {
            entry["source"]: entry["destination"] for entry in config.get("rewrites", [])
        }
        assert rewrites["/cubi"] == "/api/shell?__path=cubi"
        assert rewrites["/cubi/:path*"] == "/api/shell?__path=cubi/:path*"
        assert rewrites["/ai-workbench"] == "/api/shell?__path=ai-workbench"
        assert rewrites["/ai-workbench/:path*"] == (
            "/api/shell?__path=ai-workbench/:path*"
        )


def test_deployment_builds_stage_the_enterprise_and_workbench_documents() -> None:
    runtime_stage = (ROOT / "apps" / "web" / "scripts" / "prepare-vercel-runtime.mjs").read_text(
        encoding="utf-8"
    )
    for name in ("enterprise.html", "ai-workbench.html", "ai-workbench.css"):
        assert f'"{name}"' in runtime_stage

    root_build = (ROOT / "scripts" / "vercel_build.sh").read_text(encoding="utf-8")
    for name in ("enterprise.html", "ai-workbench.html", "ai-workbench.css"):
        assert name in root_build

    pages_build = (ROOT / "apps" / "web" / "scripts" / "assemble-pages-site.mjs").read_text(
        encoding="utf-8"
    )
    for name in ("enterprise.html", "ai-workbench.html", "ai-workbench.css"):
        assert f'"{name}"' in pages_build
