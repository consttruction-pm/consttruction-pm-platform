"""Lightweight operational metrics and correlation context.

The platform has no external metrics dependency and no background thread. This
module provides a bounded in-process counter/timer registry that a deployment
can scrape through its own instrumentation bridge, plus a context variable that
carries the request correlation id into application code.

Label values are validated and length-bounded; raw request paths, tenant ids,
document ids and user ids must never become metric labels. The HTTP middleware
uses route templates, not raw paths.
"""

from __future__ import annotations

import re
from contextvars import ContextVar, Token
from threading import RLock
from typing import Mapping

MAX_SERIES = 2_000
MAX_LABEL_VALUE = 80
_METRIC_NAME = re.compile(r"^[a-z][a-z0-9_]{1,120}$")
_LABEL_NAME = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_LABEL_VALUE = re.compile(r"^[A-Za-z0-9_.:/-]{1,80}$")

_CORRELATION: ContextVar[str | None] = ContextVar(
    "construction_pm_correlation_id", default=None
)


class ObservabilityError(ValueError):
    pass


def set_correlation_id(value: str | None) -> Token[str | None]:
    return _CORRELATION.set(value)


def reset_correlation_id(token: Token[str | None]) -> None:
    _CORRELATION.reset(token)


def current_correlation_id() -> str | None:
    return _CORRELATION.get()


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not _METRIC_NAME.match(name):
        raise ObservabilityError("INVALID_METRIC_NAME")
    return name


def _validate_labels(labels: Mapping[str, object] | None) -> tuple[tuple[str, str], ...]:
    if not labels:
        return ()
    prepared: list[tuple[str, str]] = []
    for key, value in labels.items():
        name = str(key)
        text = str(value)
        if not _LABEL_NAME.match(name):
            raise ObservabilityError("INVALID_METRIC_LABEL_NAME")
        if not _LABEL_VALUE.match(text) or len(text) > MAX_LABEL_VALUE:
            raise ObservabilityError("INVALID_METRIC_LABEL_VALUE")
        prepared.append((name, text))
    return tuple(sorted(prepared))


class OperationalMetrics:
    """Bounded, thread-safe counters and observations."""

    def __init__(self, *, max_series: int = MAX_SERIES) -> None:
        if isinstance(max_series, bool) or not isinstance(max_series, int) or max_series < 1:
            raise ObservabilityError("INVALID_METRIC_SERIES_LIMIT")
        self._max_series = max_series
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
        self._counter_series: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
        self._observations: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
        self._lock = RLock()

    def increment(
        self,
        name: str,
        *,
        labels: Mapping[str, object] | None = None,
        value: int = 1,
    ) -> None:
        metric = _validate_name(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ObservabilityError("INVALID_METRIC_INCREMENT")
        key = (metric, _validate_labels(labels))
        with self._lock:
            if key not in self._counter_series:
                if len(self._counter_series) >= self._max_series:
                    raise ObservabilityError("METRIC_SERIES_LIMIT_REACHED")
                self._counter_series.add(key)
            self._counters[key] = self._counters.get(key, 0) + value

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Mapping[str, object] | None = None,
        max_samples: int = 512,
    ) -> None:
        metric = _validate_name(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ObservabilityError("INVALID_METRIC_OBSERVATION")
        key = (metric, _validate_labels(labels))
        with self._lock:
            if key not in self._observations:
                if len(self._observations) >= self._max_series:
                    raise ObservabilityError("METRIC_SERIES_LIMIT_REACHED")
                self._observations[key] = []
            samples = self._observations[key]
            if len(samples) >= max_samples:
                samples.pop(0)
            samples.append(float(value))

    def snapshot(self) -> dict[str, object]:
        """Return a JSON-safe copy of counters and bounded observations."""
        with self._lock:
            counters = [
                {
                    "name": name,
                    "labels": dict(labels),
                    "value": value,
                }
                for (name, labels), value in sorted(self._counters.items())
            ]
            observations = [
                {
                    "name": name,
                    "labels": dict(labels),
                    "count": len(values),
                    "min": min(values) if values else 0.0,
                    "max": max(values) if values else 0.0,
                    "mean": (sum(values) / len(values)) if values else 0.0,
                }
                for (name, labels), values in sorted(self._observations.items())
            ]
        return {"counters": counters, "observations": observations}


__all__ = [
    "MAX_LABEL_VALUE",
    "MAX_SERIES",
    "ObservabilityError",
    "OperationalMetrics",
    "current_correlation_id",
    "reset_correlation_id",
    "set_correlation_id",
]
