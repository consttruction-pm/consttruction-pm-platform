#!/usr/bin/env python3
"""Validate the three reference projects workbook and print a JSON report.

Usage:
    python scripts/validate_reference_projects.py SOURCE.xlsx [--out report.json]

Exit code 0 means the workbook is internally consistent and safe to hand to the
persistence stage; 1 means at least one error was reported. Nothing is written to
a database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from construction_pm.importing import build_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="path to the reference projects workbook")
    parser.add_argument("--out", help="write the JSON report to this path")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print only counts and the issue list instead of the full sheet report",
    )
    args = parser.parse_args(argv)

    report = build_report(args.source)
    payload = report.as_dict()
    if args.summary:
        payload = {
            "contract_version": payload["contract_version"],
            "source": payload["source"],
            "ok": payload["ok"],
            "error_count": payload["error_count"],
            "warning_count": payload["warning_count"],
            "engineering_counts": {
                name: payload["counts"][name]
                for name in (
                    "EPS",
                    "OBS",
                    "WBS",
                    "Activities",
                    "Activity Relationships",
                    "Calendars",
                    "Resource Master",
                    "Resource Assignments",
                    "Baselines",
                    "Risk Register",
                    "Document Register",
                )
                if name in payload["counts"]
            },
            "issues": payload["issues"],
        }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"report written to {args.out}")
    else:
        print(text)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
