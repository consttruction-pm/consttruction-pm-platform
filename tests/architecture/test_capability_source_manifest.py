# ENT13-MANIFEST-01 — manifest schema and changed-code gate acceptance coverage.
# ENT13-PROCUREMENT-CORE-01 — existing RFQ/quote/bid/PO/commitment/delivery boundary acceptance reference.

import json
from pathlib import Path

from scripts.validate_capability_sources import (
    load_manifests,
    validate_changed_implementation_paths,
)


def _write_manifest(root: Path, *, status="implementation-ready", gaps=None):
    docs = root / "docs" / "capabilities"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "lifecycle.md").write_text("lifecycle", encoding="utf-8")
    (docs / "permissions.md").write_text("permissions", encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / "test_acceptance.py").write_text("# ENT99-AT-01 acceptance fixture\n", encoding="utf-8")
    payload = {
        "schema_version": 1,
        "capabilities": [{
            "id": "ENT-99",
            "canonical_owner": "Enterprise",
            "environments": ["Enterprise"],
            "status": status,
            "inheritance_type": "exact",
            "implementation_paths": ["apps/example/**"],
            "sources": [{
                "kind": "software_help",
                "product": "Oracle Example",
                "release": "26",
                "topic": "Example Help topic",
                "help_url": "https://docs.oracle.com/example/help.html",
                "official": True,
                "source_status": "verified"
            }],
            "formula_policy": "none",
            "formulas": [],
            "lifecycle_model": "docs/capabilities/lifecycle.md",
            "permission_matrix": "docs/capabilities/permissions.md",
            "acceptance_tests": [{"id": "ENT99-AT-01", "path": "tests/test_acceptance.py"}],
            "open_gaps": gaps or []
        }]
    }
    (docs / "capability.sources.yaml").write_text(json.dumps(payload), encoding="utf-8")


def test_manifest_passes_with_complete_references(tmp_path):
    _write_manifest(tmp_path)
    capabilities, errors = load_manifests(tmp_path)
    assert errors == []
    assert [item["id"] for item in capabilities] == ["ENT-99"]


def test_manifest_rejects_missing_help_url(tmp_path):
    _write_manifest(tmp_path)
    path = tmp_path / "docs" / "capabilities" / "capability.sources.yaml"
    payload = json.loads(path.read_text())
    payload["capabilities"][0]["sources"][0]["help_url"] = ""
    path.write_text(json.dumps(payload))
    _, errors = load_manifests(tmp_path)
    assert any("help_url" in error for error in errors)


def test_manifest_rejects_implementation_ready_with_open_gaps(tmp_path):
    _write_manifest(tmp_path, gaps=["MISSING / VERIFY: current release topic crosswalk"])
    _, errors = load_manifests(tmp_path)
    assert any("cannot have open_gaps" in error for error in errors)


def test_changed_code_requires_implementation_ready_manifest(tmp_path):
    _write_manifest(tmp_path, status="source-mapped")
    capabilities, errors = load_manifests(tmp_path)
    assert errors == []
    errors = validate_changed_implementation_paths(
        ["apps/example/src/feature.ts"], capabilities
    )
    assert len(errors) == 1
    assert "not implementation-ready" in errors[0]


def test_changed_code_without_manifest_mapping_is_rejected(tmp_path):
    _write_manifest(tmp_path)
    capabilities, errors = load_manifests(tmp_path)
    assert errors == []
    errors = validate_changed_implementation_paths(
        ["src/unmapped/new_feature.py"], capabilities
    )
    assert len(errors) == 1
    assert "no capability.sources.yaml" in errors[0]
