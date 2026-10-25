#!/usr/bin/env python3
"""Generate the public-safe Web scheduling reference view from the authoritative registry.

The full compatibility registry remains developer metadata. This generated view
contains rewritten requirement summaries, options, formula contracts and review states.
Official source names/URLs and internal source/test paths are intentionally excluded.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from construction_pm.p6_code_reference import (  # noqa: E402
    FORMULA_REFERENCE,
    P6_CODE_REFERENCE,
    P6_DOCUMENTATION_AUDIT,
    REFERENCE_AS_OF,
    REFERENCE_VERSION,
)

OUTPUT = ROOT / "apps" / "web" / "src" / "scheduling-reference-catalog.generated.ts"
HEADER = (
    "/** Generated from the compatibility registry. "
    "Do not hand-edit; run scripts/generate_web_scheduling_reference.py. */\n"
    "export const SCHEDULING_REFERENCE_CATALOG = "
)
FOOTER = " as const;\n\nexport type SchedulingReferenceCatalog = typeof SCHEDULING_REFERENCE_CATALOG;\n"


def _scrub(value: object) -> object:
    if isinstance(value, tuple):
        return [_scrub(item) for item in value]
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if not isinstance(value, str):
        return value

    value = re.sub(r"https?://[^\s)\"']+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bOracle\b", "documented source", value, flags=re.IGNORECASE)
    value = re.sub(r"\bPrimavera\b", "reference scheduler", value, flags=re.IGNORECASE)
    value = re.sub(r"\bP6\b", "reference scheduler", value, flags=re.IGNORECASE)
    value = re.sub(r"\bP6[-_][A-Za-z0-9_./-]+", "implementation component", value)
    value = re.sub(r"(?:src|tests?|docs)/[A-Za-z0-9_./-]+", "internal reference", value)
    value = re.sub(
        r"\x60([^\x60]+)\x60",
        lambda match: re.sub(r"[A-Z0-9_./-]{2,}", "internal reference", _scrub(match.group(1))),
        value,
    )
    return re.sub(r"\s{2,}", " ", value).strip()


def _requirement(item: object) -> dict[str, object]:
    row = asdict(item)
    return {
        "id": row["id"],
        "area": _scrub(row["area"]),
        "feature": _scrub(row["feature"]),
        "semantics": _scrub(row["required_semantics"]),
        "options": _scrub(row["user_options"]),
        "status": row["coverage"],
        "gap": _scrub(row["known_gap"]),
    }


def _formula(item: object) -> dict[str, object]:
    row = asdict(item)
    return {
        "id": row["id"],
        "feature": _scrub(row["feature"]),
        "algorithm": _scrub(row["formula_or_algorithm"]),
        "inputs": _scrub(row["input_fields"]),
        "options": _scrub(row["controlling_options"]),
        "calendarRules": _scrub(row["units_and_calendar_rules"]),
        "edgeCases": _scrub(row["edge_cases"]),
        "status": _scrub(row["status"]),
        "gap": _scrub(row["known_gap"]),
    }


def _documentation(item: object) -> dict[str, object]:
    row = asdict(item)
    return {
        "id": re.sub(r"\bP6\b", "REF", row["id"], flags=re.IGNORECASE),
        "title": _scrub(row["title"]),
        "scope": _scrub(row["product_scope"]),
        "status": _scrub(row["review_status"]),
        "reviewed": _scrub(row["reviewed_scope"]),
        "remaining": _scrub(row["remaining_work"]),
        "requirements": _scrub(row["linked_requirement_ids"]),
    }


def render() -> str:
    catalog = {
        "version": REFERENCE_VERSION,
        "asOf": REFERENCE_AS_OF,
        "requirements": [_requirement(item) for item in P6_CODE_REFERENCE],
        "formulas": [_formula(item) for item in FORMULA_REFERENCE],
        "documentation": [_documentation(item) for item in P6_DOCUMENTATION_AUDIT],
    }
    return HEADER + json.dumps(catalog, ensure_ascii=False, indent=2) + FOOTER


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated Web catalog is stale")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.is_file():
            print(f"missing generated catalog: {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        actual = OUTPUT.read_text(encoding="utf-8")
        if actual != expected:
            print("Web scheduling reference catalog is stale; run scripts/generate_web_scheduling_reference.py", file=sys.stderr)
            return 1
        print("Web scheduling reference catalog is current.")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"generated {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
