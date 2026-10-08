#!/usr/bin/env python3
"""Prevent legacy Resource infrastructure imports from escaping the Resource package."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "construction_pm"
LEGACY_MODULES = (
    "construction_pm.resources.context",
    "construction_pm.resources.transactions",
    "construction_pm.resources.idempotency",
)
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([^#]+)")


def main() -> int:
    violations: list[str] = []
    resource_root = SRC / "resources"

    for path in sorted(SRC.rglob("*.py")):
        try:
            path.relative_to(resource_root)
        except ValueError:
            pass
        else:
            continue

        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), 1):
            match = IMPORT_RE.match(line)
            if not match:
                continue
            imported = match.group(1).strip()
            for legacy in LEGACY_MODULES:
                if legacy in imported:
                    violations.append(f"{path.relative_to(ROOT)}:{line_no}: {legacy}")

    if violations:
        print("Legacy Resource infrastructure imports escaped resources/:")
        print("\n".join(violations))
        return 1

    print("Legacy Resource infrastructure boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
