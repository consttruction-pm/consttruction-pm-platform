#!/usr/bin/env python3
"""Read-only staging smoke test CLI (see construction_pm.staging_smoke)."""

from __future__ import annotations

import sys

from construction_pm.staging_smoke import main

if __name__ == "__main__":
    sys.exit(main())
