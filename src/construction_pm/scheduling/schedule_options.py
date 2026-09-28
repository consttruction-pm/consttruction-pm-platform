from __future__ import annotations

from enum import Enum


class StartToStartLagCalculationType(str, Enum):
    """P6 start-to-start out-of-sequence lag calculation mode."""

    EARLY_START = "EARLY_START"
    ACTUAL_START = "ACTUAL_START"


def start_to_start_lag_type_from_p6(value: bool) -> StartToStartLagCalculationType:
    """Map the P6 boolean field to the typed Shared Core option.

    P6 exposes StartToStartLagCalculationType as a boolean at the API boundary:
    False = Early Start, True = Actual Start.
    """
    if not isinstance(value, bool):
        raise TypeError("P6 StartToStartLagCalculationType must be a bool")
    return (
        StartToStartLagCalculationType.ACTUAL_START
        if value
        else StartToStartLagCalculationType.EARLY_START
    )


def start_to_start_lag_type_to_p6(
    value: StartToStartLagCalculationType,
) -> bool:
    """Map the typed Shared Core option back to the P6 boolean contract."""
    if not isinstance(value, StartToStartLagCalculationType):
        raise TypeError(
            "start_to_start_lag_calculation_type must be a StartToStartLagCalculationType"
        )
    return value is StartToStartLagCalculationType.ACTUAL_START
