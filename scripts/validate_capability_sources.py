#!/usr/bin/env python3
"""Validate machine-readable capability inheritance manifests.

The .yaml files use the JSON-compatible YAML subset so validation needs only
the Python standard library and behaves identically on every CI runner.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOTS = ("apps/", "src/", "api/", "shared/")
VALID_STATUS = {"source-mapped", "implementation-ready", "blocked"}
VALID_INHERITANCE = {"exact", "additive", "adapted", "cubi-native"}
VALID_FORMULA_POLICY = {"local", "delegated", "none"}


class ManifestError(ValueError):
    pass


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _relative_file(root: Path, value: Any, label: str, errors: list[str]) -> None:
    if not _nonempty(value):
        errors.append(f"{label}: expected a non-empty repository-relative path")
        return
    path = (root / value).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        errors.append(f"{label}: path escapes repository root: {value}")
    elif not path.is_file():
        errors.append(f"{label}: referenced file does not exist: {value}")


def validate_capability(cap: Any, root: Path, manifest_path: Path) -> list[str]:
    errors: list[str] = []
    prefix = f"{manifest_path}: "
    if not isinstance(cap, dict):
        return [prefix + "each capability entry must be an object"]

    required = (
        "id", "canonical_owner", "environments", "status", "inheritance_type",
        "implementation_paths", "sources", "formula_policy", "formulas",
        "lifecycle_model", "permission_matrix", "acceptance_tests",
    )
    for key in required:
        if key not in cap:
            errors.append(prefix + f"missing required field '{key}'")

    if not _nonempty(cap.get("id")):
        errors.append(prefix + "id must be a non-empty string")
    if cap.get("canonical_owner") not in {"Engineering", "Enterprise", "Shared", "Workbench"}:
        errors.append(prefix + "canonical_owner must be Engineering, Enterprise, Shared or Workbench")
    if not isinstance(cap.get("environments"), list) or not cap["environments"]:
        errors.append(prefix + "environments must be a non-empty array")
    elif any(x not in {"Engineering", "Enterprise", "Workbench"} for x in cap["environments"]):
        errors.append(prefix + "environments contains an unsupported environment")
    if cap.get("status") not in VALID_STATUS:
        errors.append(prefix + f"status must be one of {sorted(VALID_STATUS)}")
    if cap.get("inheritance_type") not in VALID_INHERITANCE:
        errors.append(prefix + f"inheritance_type must be one of {sorted(VALID_INHERITANCE)}")

    implementation_paths = cap.get("implementation_paths")
    if not isinstance(implementation_paths, list) or any(not _nonempty(p) for p in implementation_paths):
        errors.append(prefix + "implementation_paths must be an array of non-empty path globs")

    sources = cap.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(prefix + "sources must contain at least one software Help or standard reference")
        sources = []
    software_help_count = 0
    for index, source in enumerate(sources):
        label = f"{prefix}sources[{index}]"
        if not isinstance(source, dict):
            errors.append(label + " must be an object")
            continue
        for key in ("kind", "product", "release", "topic", "help_url", "source_status"):
            if not _nonempty(source.get(key)):
                errors.append(label + f" requires non-empty '{key}'")
        if source.get("kind") == "software_help":
            software_help_count += 1
            url = source.get("help_url", "")
            if not isinstance(url, str) or not url.startswith("https://docs.oracle.com/"):
                errors.append(label + " software_help URL must be an official Oracle documentation URL")
            if source.get("official") is not True:
                errors.append(label + " software_help must explicitly set official=true")
            if source.get("source_status") not in {"verified", "anchor_only", "missing_verify"}:
                errors.append(label + " source_status must be verified, anchor_only or missing_verify")
        elif source.get("kind") in {"theory", "domain_standard"}:
            if not isinstance(source.get("help_url"), str) or not source["help_url"].startswith("https://"):
                errors.append(label + " standard reference must have an https URL")
        else:
            errors.append(label + " kind must be software_help, theory or domain_standard")
    if cap.get("inheritance_type") != "cubi-native" and software_help_count == 0:
        errors.append(prefix + "non-CUBI-native capability requires at least one software_help source")

    formula_policy = cap.get("formula_policy")
    formulas = cap.get("formulas")
    if formula_policy not in VALID_FORMULA_POLICY:
        errors.append(prefix + f"formula_policy must be one of {sorted(VALID_FORMULA_POLICY)}")
    if not isinstance(formulas, list):
        errors.append(prefix + "formulas must be an array")
        formulas = []
    if formula_policy in {"delegated", "none"} and formulas:
        errors.append(prefix + f"formula_policy={formula_policy} requires formulas=[]")
    if formula_policy == "delegated":
        if not _nonempty(cap.get("delegated_owner")) or not _nonempty(cap.get("delegated_service")):
            errors.append(prefix + "delegated formula policy requires delegated_owner and delegated_service")
    if formula_policy == "local":
        if not formulas:
            errors.append(prefix + "formula_policy=local requires at least one formula")
        for index, formula in enumerate(formulas):
            label = f"{prefix}formulas[{index}]"
            if not isinstance(formula, dict):
                errors.append(label + " must be an object")
                continue
            for key in ("formula_id", "expression", "unit", "rounding", "expected_test_id", "test_path"):
                if not _nonempty(formula.get(key)):
                    errors.append(label + f" requires non-empty '{key}'")
            if not isinstance(formula.get("variables"), list) or not formula["variables"]:
                errors.append(label + " requires a non-empty variables array")
            _relative_file(root, formula.get("test_path"), label + ".test_path", errors)
            if _nonempty(formula.get("test_path")) and _nonempty(formula.get("expected_test_id")):
                test_file = root / formula["test_path"]
                if test_file.is_file() and formula["expected_test_id"] not in test_file.read_text(encoding="utf-8"):
                    errors.append(label + f" expected_test_id {formula['expected_test_id']} is not present in its test file")

    _relative_file(root, cap.get("lifecycle_model"), prefix + "lifecycle_model", errors)
    _relative_file(root, cap.get("permission_matrix"), prefix + "permission_matrix", errors)

    tests = cap.get("acceptance_tests")
    if not isinstance(tests, list) or not tests:
        errors.append(prefix + "acceptance_tests must be a non-empty array")
    else:
        for index, test in enumerate(tests):
            label = f"{prefix}acceptance_tests[{index}]"
            if not isinstance(test, dict) or not _nonempty(test.get("id")):
                errors.append(label + " requires an id")
                continue
            _relative_file(root, test.get("path"), label + ".path", errors)
            if _nonempty(test.get("path")) and test.get("path"):
                test_file = root / test["path"]
                if test_file.is_file() and test["id"] not in test_file.read_text(encoding="utf-8"):
                    errors.append(label + f" id {test['id']} is not present in its test file")

    gaps = cap.get("open_gaps", [])
    if not isinstance(gaps, list):
        errors.append(prefix + "open_gaps must be an array when provided")
        gaps = []
    if cap.get("status") == "implementation-ready":
        if gaps:
            errors.append(prefix + "implementation-ready capability cannot have open_gaps")
        if not implementation_paths:
            errors.append(prefix + "implementation-ready capability must declare implementation_paths")
        if any(s.get("kind") == "software_help" and s.get("source_status") != "verified"
               for s in sources if isinstance(s, dict)):
            errors.append(prefix + "implementation-ready capability has unverified software Help sources")
    return errors


def load_manifests(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    manifests = sorted(root.rglob("capability.sources.yaml"))
    errors: list[str] = []
    capabilities: list[dict[str, Any]] = []
    seen: dict[str, Path] = {}
    for path in manifests:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: expected valid JSON-compatible YAML: {exc}")
            continue
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            errors.append(f"{path}: schema_version must be 1")
            continue
        entries = data.get("capabilities")
        if not isinstance(entries, list) or not entries:
            errors.append(f"{path}: capabilities must be a non-empty array")
            continue
        for cap in entries:
            errors.extend(validate_capability(cap, root, path.relative_to(root)))
            if isinstance(cap, dict) and _nonempty(cap.get("id")):
                cap_id = cap["id"]
                if cap_id in seen:
                    errors.append(f"duplicate capability id {cap_id}: {seen[cap_id]} and {path.relative_to(root)}")
                else:
                    seen[cap_id] = path.relative_to(root)
                capabilities.append({**cap, "_manifest": path.relative_to(root).as_posix()})
    if not manifests:
        errors.append("no capability.sources.yaml manifest found")
    return capabilities, errors


def changed_paths(root: Path, base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=root, check=True, capture_output=True, text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_changed_implementation_paths(changed: list[str], capabilities: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    implementation_changes = [
        path for path in changed
        if path.startswith(IMPLEMENTATION_ROOTS)
        and not path.endswith(("capability.sources.yaml",))
    ]
    for path in implementation_changes:
        matches = [
            cap for cap in capabilities
            if any(fnmatch.fnmatchcase(path, pattern) for pattern in cap.get("implementation_paths", []))
        ]
        if not matches:
            errors.append(
                f"{path}: no capability.sources.yaml implementation_paths entry covers this code change; "
                "add/update the capability manifest in the same PR"
            )
            continue
        if len(matches) > 1:
            errors.append(f"{path}: mapped to multiple capability owners: {', '.join(c['id'] for c in matches)}")
            continue
        cap = matches[0]
        if cap.get("status") != "implementation-ready":
            errors.append(
                f"{path}: {cap['id']} is {cap.get('status')}, not implementation-ready; "
                "complete the Help crosswalk, formula/lifecycle/security evidence first"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base-ref", help="Git ref used to detect changed implementation files (PR CI only)")
    args = parser.parse_args()
    root = args.root.resolve()
    capabilities, errors = load_manifests(root)
    if args.base_ref:
        try:
            changed = changed_paths(root, args.base_ref)
            errors.extend(validate_changed_implementation_paths(changed, capabilities))
        except subprocess.CalledProcessError as exc:
            errors.append(f"could not diff base ref {args.base_ref}: {exc.stderr.strip()}")
    if errors:
        print("Capability source validation FAILED:")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"Capability source validation PASSED: {len(capabilities)} capability manifest entries checked.")
    if args.base_ref:
        print(f"Changed implementation paths checked against {args.base_ref}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
