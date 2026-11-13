"""Operational metrics export boundary.

The platform keeps operational metrics in a bounded in-process registry. This
module adds a deliberately small, dependency-free exporter that turns a bounded
snapshot into deterministic Prometheus text exposition, plus the configuration
and access policy for an optional scrape endpoint.

Design constraints:

- **Bounded.** The registry caps series. Export additionally caps output bytes;
  exceeding the cap fails closed instead of truncating a partial exposition.
- **Deterministic.** Series are sorted by metric name and then by label set, and
  numbers are formatted without locale or platform variation.
- **Label safety.** Labels are validated by the registry (short, no spaces, no
  free text), so tenant ids, user ids, tokens, document names and raw request
  paths cannot become label values here. This module never invents labels.
- **Fail isolated.** Rendering happens on the scrape path only. A rendering or
  configuration failure yields an ``unavailable`` result; it never raises into
  request handling and never blocks business endpoints.
- **Secrets stay secret.** The scrape token is compared in constant time and is
  never echoed in a response, event or error string.
- **No tracing claim.** This is metrics export only. There is no span exporter,
  collector, sampling or propagation, and nothing here should be described as
  distributed tracing.
"""

from __future__ import annotations

import hmac
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol, runtime_checkable

ENABLED_ENV = "CONSTRUCTION_PM_METRICS_EXPORT_ENABLED"
TOKEN_ENV = "CONSTRUCTION_PM_METRICS_EXPORT_TOKEN"
MAX_BYTES_ENV = "CONSTRUCTION_PM_METRICS_EXPORT_MAX_BYTES"
MAX_SERIES_ENV = "CONSTRUCTION_PM_METRICS_EXPORT_MAX_SERIES"

METRICS_PATH = "/api/metrics"
CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

DEFAULT_MAX_BYTES = 256 * 1024
MAX_MAX_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_SERIES = 2_000
MAX_MAX_SERIES = 20_000
MIN_TOKEN_LENGTH = 16
MAX_TOKEN_LENGTH = 512
_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSEY = frozenset({"", "0", "false", "no", "off"})
_TOKEN = re.compile(r"^[\x21-\x7e]{16,512}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class MetricsExportError(ValueError):
    """Raised internally when an exposition cannot be produced safely."""


class MetricsExportState(str, Enum):
    DISABLED = "disabled"
    CONFIGURED = "configured"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class MetricsExportSettings:
    """Scrape configuration derived from the deployment environment.

    An invalid or incomplete configuration is represented by ``error`` with the
    exporter forced to ``unavailable``; construction never raises so that a bad
    metrics configuration cannot prevent the application from starting.
    """

    enabled: bool = False
    token: str | None = None
    max_bytes: int = DEFAULT_MAX_BYTES
    max_series: int = DEFAULT_MAX_SERIES
    error: str | None = None

    @property
    def state(self) -> MetricsExportState:
        if not self.enabled:
            return MetricsExportState.DISABLED
        if self.error is not None:
            return MetricsExportState.UNAVAILABLE
        return MetricsExportState.CONFIGURED

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "MetricsExportSettings":
        raw_enabled = str(environment.get(ENABLED_ENV, "")).strip().lower()
        if raw_enabled in _FALSEY:
            return cls(enabled=False)
        if raw_enabled not in _TRUTHY:
            return cls(enabled=True, error="METRICS_EXPORT_ENABLED_INVALID")

        token = environment.get(TOKEN_ENV)
        max_bytes = _bounded_int(
            environment.get(MAX_BYTES_ENV),
            default=DEFAULT_MAX_BYTES,
            minimum=1,
            maximum=MAX_MAX_BYTES,
        )
        max_series = _bounded_int(
            environment.get(MAX_SERIES_ENV),
            default=DEFAULT_MAX_SERIES,
            minimum=1,
            maximum=MAX_MAX_SERIES,
        )
        if max_bytes is None:
            return cls(enabled=True, error="METRICS_EXPORT_MAX_BYTES_INVALID")
        if max_series is None:
            return cls(enabled=True, error="METRICS_EXPORT_MAX_SERIES_INVALID")

        if token is None or not token:
            return cls(
                enabled=True,
                max_bytes=max_bytes,
                max_series=max_series,
                error="METRICS_EXPORT_TOKEN_MISSING",
            )
        if (
            len(token) < MIN_TOKEN_LENGTH
            or len(token) > MAX_TOKEN_LENGTH
            or not _TOKEN.match(token)
        ):
            return cls(
                enabled=True,
                max_bytes=max_bytes,
                max_series=max_series,
                error="METRICS_EXPORT_TOKEN_INVALID",
            )
        return cls(
            enabled=True,
            token=token,
            max_bytes=max_bytes,
            max_series=max_series,
        )


def _bounded_int(raw: str | None, *, default: int, minimum: int, maximum: int) -> int | None:
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip(), 10)
    except (TypeError, ValueError):
        return None
    if value < minimum or value > maximum:
        return None
    return value


@runtime_checkable
class MetricsSource(Protocol):
    """Read-only boundary the exporter depends on."""

    def snapshot(self) -> Mapping[str, object]: ...


@runtime_checkable
class PrometheusTextExporter(Protocol):
    """Clean exporter seam; a deployment may substitute its own renderer."""

    def render(self, snapshot: Mapping[str, object]) -> str: ...


@dataclass(frozen=True)
class ScrapeResult:
    state: MetricsExportState
    body: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.state is MetricsExportState.CONFIGURED and self.error is None


def format_number(value: float | int) -> str:
    """Format a finite number deterministically for the exposition format."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MetricsExportError("METRICS_EXPORT_VALUE_INVALID")
    if isinstance(value, float) and not math.isfinite(value):
        raise MetricsExportError("METRICS_EXPORT_VALUE_NOT_FINITE")
    if isinstance(value, int):
        return str(value)
    if value.is_integer():
        return str(int(value))
    return repr(value)


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _label_block(labels: Mapping[str, str]) -> str:
    if not labels:
        return ""
    rendered = ",".join(
        f'{name}="{_escape_label(str(labels[name]))}"' for name in sorted(labels)
    )
    return "{" + rendered + "}"


class DeterministicPrometheusExporter:
    """Render a bounded registry snapshot as stable Prometheus text.

    Counters render as ``<name>``; observations render as ``<name>_count``,
    ``_sum``, ``_min``, ``_max`` and ``_mean``. With no labels a sample has no
    braces, which keeps the output minimal and valid. Output order is total and
    independent of registry insertion order.
    """

    def __init__(self, *, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
            raise MetricsExportError("METRICS_EXPORT_MAX_BYTES_INVALID")
        self._max_bytes = max_bytes

    def render(self, snapshot: Mapping[str, object]) -> str:
        counters = snapshot.get("counters", [])
        observations = snapshot.get("observations", [])
        if not isinstance(counters, (list, tuple)) or not isinstance(
            observations, (list, tuple)
        ):
            raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")

        lines: list[tuple[str, str, int, str]] = []
        for item in counters:
            name, labels, value = _counter_parts(item)
            block = _label_block(labels)
            lines.append((name, block, 0, f"{name}{block} {format_number(value)}"))
        for item in observations:
            name, labels, values = _observation_parts(item)
            block = _label_block(labels)
            count, total, minimum, maximum, mean = values
            lines.append((name, block, 1, f"{name}_count{block} {format_number(count)}"))
            lines.append((name, block, 2, f"{name}_sum{block} {format_number(total)}"))
            lines.append((name, block, 3, f"{name}_min{block} {format_number(minimum)}"))
            lines.append((name, block, 4, f"{name}_max{block} {format_number(maximum)}"))
            lines.append((name, block, 5, f"{name}_mean{block} {format_number(mean)}"))

        lines.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
        body = "".join(entry[3] + "\n" for entry in lines)
        if len(body.encode("utf-8")) > self._max_bytes:
            raise MetricsExportError("METRICS_EXPORT_OUTPUT_LIMIT_EXCEEDED")
        return body


def _counter_parts(item: object) -> tuple[str, dict[str, str], int]:
    if not isinstance(item, Mapping):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    name = _metric_name(item.get("name"))
    labels = _labels(item.get("labels"))
    value = item.get("value")
    if isinstance(value, bool) or not isinstance(value, int):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    return name, labels, value


def _observation_parts(
    item: object,
) -> tuple[str, dict[str, str], tuple[int, float, float, float, float]]:
    if not isinstance(item, Mapping):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    name = _metric_name(item.get("name"))
    labels = _labels(item.get("labels"))
    count = item.get("count")
    minimum = item.get("min")
    maximum = item.get("max")
    mean = item.get("mean")
    total = item.get("sum")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    for value in (minimum, maximum, mean):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
        if isinstance(value, float) and not math.isfinite(value):
            raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    if total is None:
        # Older or custom sources may omit the sum; it is exactly recoverable
        # from count * mean, so do not fail an otherwise valid exposition.
        total = float(mean) * count
    elif isinstance(total, bool) or not isinstance(total, (int, float)):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    elif isinstance(total, float) and not math.isfinite(total):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    return name, labels, (count, float(total), float(minimum), float(maximum), float(mean))


def _metric_name(value: object) -> str:
    if not isinstance(value, str) or not value or _CONTROL.search(value):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    if not re.match(r"^[a-z][a-z0-9_]{1,120}$", value):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    return value


def _labels(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
    prepared: dict[str, str] = {}
    for key, label in value.items():
        if not isinstance(key, str) or not isinstance(label, str):
            raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
        if not re.match(r"^[a-z][a-z0-9_]{0,40}$", key):
            raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
        if _CONTROL.search(label) or len(label) > 80:
            raise MetricsExportError("METRICS_EXPORT_SNAPSHOT_INVALID")
        prepared[key] = label
    return prepared


class MetricsExportService:
    """Access policy and failure isolation around a metrics exporter."""

    def __init__(
        self,
        metrics: MetricsSource | None,
        *,
        settings: MetricsExportSettings | None = None,
        exporter: PrometheusTextExporter | None = None,
    ) -> None:
        self._metrics = metrics
        self._settings = settings or MetricsExportSettings()
        self._exporter = exporter or DeterministicPrometheusExporter(
            max_bytes=self._settings.max_bytes
        )

    @property
    def settings(self) -> MetricsExportSettings:
        return self._settings

    @property
    def state(self) -> MetricsExportState:
        if not self._settings.enabled:
            return MetricsExportState.DISABLED
        if self._settings.error is not None or self._metrics is None:
            return MetricsExportState.UNAVAILABLE
        return MetricsExportState.CONFIGURED

    def authorized(self, authorization: str | None) -> bool:
        """Constant-time bearer check; never reveals which part was wrong."""
        token = self._settings.token
        if token is None:
            return False
        supplied = ""
        if isinstance(authorization, str):
            scheme, _, candidate = authorization.strip().partition(" ")
            if scheme.lower() == "bearer":
                supplied = candidate.strip()
        return hmac.compare_digest(supplied.encode("utf-8"), token.encode("utf-8"))

    def scrape(self) -> ScrapeResult:
        """Render once; never raise into the request path."""
        state = self.state
        if state is not MetricsExportState.CONFIGURED:
            return ScrapeResult(
                state=state,
                error=self._settings.error
                if self._settings.error is not None
                else "METRICS_EXPORT_UNAVAILABLE",
            )
        assert self._metrics is not None
        try:
            snapshot = self._metrics.snapshot()
            counters = snapshot.get("counters", ())
            observations = snapshot.get("observations", ())
            series = len(counters) + len(observations)
            if series > self._settings.max_series:
                return ScrapeResult(
                    state=MetricsExportState.UNAVAILABLE,
                    error="METRICS_EXPORT_SERIES_LIMIT_EXCEEDED",
                )
            body = self._exporter.render(snapshot)
        except Exception as exc:
            # Never propagate exporter failure into business request handling,
            # and never echo an exception message that could contain values.
            code = (
                str(exc)
                if isinstance(exc, MetricsExportError)
                else type(exc).__name__
            )
            return ScrapeResult(state=MetricsExportState.UNAVAILABLE, error=code)
        if not isinstance(body, str) or len(body.encode("utf-8")) > self._settings.max_bytes:
            return ScrapeResult(
                state=MetricsExportState.UNAVAILABLE,
                error="METRICS_EXPORT_OUTPUT_LIMIT_EXCEEDED",
            )
        return ScrapeResult(state=MetricsExportState.CONFIGURED, body=body)


__all__ = [
    "CONTENT_TYPE",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_SERIES",
    "DeterministicPrometheusExporter",
    "ENABLED_ENV",
    "MAX_BYTES_ENV",
    "MAX_SERIES_ENV",
    "METRICS_PATH",
    "MetricsExportError",
    "MetricsExportService",
    "MetricsExportSettings",
    "MetricsExportState",
    "MetricsSource",
    "PrometheusTextExporter",
    "ScrapeResult",
    "TOKEN_ENV",
    "format_number",
]
