from __future__ import annotations

from enum import Enum


class StartToStartLagCalculationType(str, Enum):
    """P6 start-to-start out-of-sequence lag calculation mode."""

    EARLY_START = "EARLY_START"
    ACTUAL_START = "ACTUAL_START"
