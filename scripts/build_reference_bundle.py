#!/usr/bin/env python3
"""Validate the workbook and freeze it into the import bundle.

Usage:
    python scripts/build_reference_bundle.py SOURCE.xlsx [--out PATH]

Refuses to write a bundle when the source has validation errors.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from construction_pm.importing import build_report  # noqa: E402
from construction_pm.importing.reference_bundle import (  # noqa: E402
    build_bundle,
    write_bundle,
)

DEFAULT_OUT = ROOT / "src" / "construction_pm" / "importing" / "data" / (
    "cubi_reference_projects.v1.json.gz"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="path to the reference projects workbook")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="bundle path")
    args = parser.parse_args(argv)

    report = build_report(args.source)
    if not report.ok:
        print(
            f"refusing to build a bundle: {len(report.errors)} validation errors",
            file=sys.stderr,
        )
        for issue in report.errors[:10]:
            print(
                f"  {issue.code} {issue.sheet} {issue.record}: {issue.detail}",
                file=sys.stderr,
            )
        return 1

    bundle = build_bundle(report.dataset)
    target = write_bundle(bundle, args.out)
    payload = target.read_bytes()
    print(f"bundle written to {target}")
    print(f"sha256 {hashlib.sha256(payload).hexdigest()}")
    print(f"bytes {len(payload)}")
    for project_id, entry in bundle["projects"].items():
        print(
            f"{project_id}: activities={len(entry['activities'])} "
            f"relationships={len(entry['activity_relationships'])} "
            f"wbs={len(entry['wbs'])} resources={len(entry['resource_master'])} "
            f"equipment={len(entry['equipment_register'])} "
            f"assignments={len(entry['resource_assignments'])} "
            f"baseline_activities={len(entry['baseline_activities'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
