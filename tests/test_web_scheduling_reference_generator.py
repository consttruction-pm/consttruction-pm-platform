from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_web_scheduling_reference_catalog_is_generated_from_authoritative_registry() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_web_scheduling_reference.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
