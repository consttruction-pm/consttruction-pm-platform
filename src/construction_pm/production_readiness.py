"""Production configuration validation, readiness probes and structured events.

This module is the operational boundary for Issue #1799 Workstream 7. It does
not deploy anything and it never contacts a cloud provider. It validates the
environment a deployment intends to use, aggregates component readiness so a
mandatory dependency is distinguishable from an optional one, and emits
structured events carrying a correlation id without logging payloads, tokens
or credentials.

Configuration errors name environment variables and stable codes only. Secret
values are never copied into a report, a log record or an exception message.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Iterable, Mapping, TextIO
from urllib.parse import urlsplit

from .document_object_storage import (
    DocumentStorageConfigurationError,
    s3_settings_from_environment,
)

PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})
KNOWN_ENVIRONMENTS = frozenset(
    {"development", "dev", "test", "testing", "staging", "production", "prod"}
)
COMPONENT_NAMES = (
    "configuration",
    "database",
    "object_storage",
    "malware_scanner",
    "ocr",
    "job_queue",
    "retention",
    "observability",
)

_LOG_LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})
_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SAFE_DETAIL = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
_REDACT_KEY_PARTS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "content",
    "payload",
    "body",
    "bytes",
)


class ProductionReadinessError(ValueError):
    """An operational configuration value or readiness contract is invalid."""


class Requirement(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class ReadinessStatus(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    NOT_READY = "not_ready"


@dataclass(frozen=True)
class ConfigurationIssue:
    code: str
    variable: str
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {"code": self.code, "variable": self.variable}
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass(frozen=True)
class EnvironmentValidation:
    """Result of validating an environment mapping.

    ``components`` records whether a service is explicitly configured.
    ``component_problems`` contains stable codes per component (never values).
    """

    environment: str
    production: bool
    errors: tuple[ConfigurationIssue, ...] = ()
    warnings: tuple[ConfigurationIssue, ...] = ()
    components: Mapping[str, bool] = field(default_factory=dict)
    component_problems: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "environment": self.environment,
            "production": self.production,
            "valid": self.valid,
            "components": dict(self.components),
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
        }


def _text(env: Mapping[str, str], name: str) -> str:
    return str(env.get(name) or "").strip()


def _lower(env: Mapping[str, str], name: str) -> str:
    return _text(env, name).lower()


def _truth(value: str) -> bool:
    return value in {"1", "true", "yes", "on"}


def _is_production(
    env: Mapping[str, str], production: bool | None
) -> bool:
    if production is not None:
        return bool(production)
    return _lower(env, "CONSTRUCTION_PM_ENVIRONMENT") in PRODUCTION_ENVIRONMENTS


def _validate_url(
    name: str,
    value: str,
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
    require_https: bool,
) -> bool:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        errors.append(ConfigurationIssue("INVALID_URL", name))
        return False
    if production and require_https and parsed.scheme != "https":
        errors.append(ConfigurationIssue("URL_REQUIRES_HTTPS", name))
        return False
    if not production and parsed.scheme != "https":
        warnings.append(ConfigurationIssue("URL_NOT_HTTPS", name))
    return True


def _validate_database(
    env: Mapping[str, str],
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
) -> tuple[bool, list[str]]:
    primary = _text(env, "CONSTRUCTION_PM_DATABASE_URL")
    legacy = _text(env, "CONSTRUCTION_PM_POSTGRES_DSN")
    problems: list[str] = []
    if not primary and not legacy:
        if production:
            errors.append(
                ConfigurationIssue(
                    "MISSING_DATABASE_URL", "CONSTRUCTION_PM_DATABASE_URL"
                )
            )
            problems.append("MISSING_DATABASE_URL")
        return False, problems
    if primary and legacy and primary != legacy:
        warnings.append(
            ConfigurationIssue(
                "DATABASE_URL_CONFLICT",
                "CONSTRUCTION_PM_DATABASE_URL",
                "both database variables are set with different values; the primary wins",
            )
        )
    value = primary or legacy
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme not in {"postgres", "postgresql", "sqlite"} or not (
        parsed.netloc or scheme == "sqlite"
    ):
        errors.append(ConfigurationIssue("INVALID_DATABASE_URL", "CONSTRUCTION_PM_DATABASE_URL"))
        problems.append("INVALID_DATABASE_URL")
        return False, problems
    if production and scheme == "sqlite":
        errors.append(
            ConfigurationIssue(
                "SQLITE_FORBIDDEN_IN_PRODUCTION", "CONSTRUCTION_PM_DATABASE_URL"
            )
        )
        problems.append("SQLITE_FORBIDDEN_IN_PRODUCTION")
        return False, problems
    return True, problems


def _validate_storage(
    env: Mapping[str, str],
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
) -> tuple[bool, list[str]]:
    kind = _lower(env, "CONSTRUCTION_PM_DOCUMENT_STORAGE")
    problems: list[str] = []
    if not kind:
        if production:
            errors.append(
                ConfigurationIssue(
                    "MISSING_DOCUMENT_STORAGE", "CONSTRUCTION_PM_DOCUMENT_STORAGE"
                )
            )
            problems.append("MISSING_DOCUMENT_STORAGE")
        return False, problems
    if kind not in {"local", "s3"}:
        errors.append(
            ConfigurationIssue("INVALID_DOCUMENT_STORAGE_KIND", "CONSTRUCTION_PM_DOCUMENT_STORAGE")
        )
        problems.append("INVALID_DOCUMENT_STORAGE_KIND")
        return False, problems
    if kind == "local":
        if production:
            errors.append(
                ConfigurationIssue(
                    "LOCAL_STORAGE_FORBIDDEN_IN_PRODUCTION",
                    "CONSTRUCTION_PM_DOCUMENT_STORAGE",
                )
            )
            problems.append("LOCAL_STORAGE_FORBIDDEN_IN_PRODUCTION")
            return False, problems
        return True, problems
    try:
        s3_settings_from_environment(env)
    except DocumentStorageConfigurationError as exc:
        code = str(exc)
        variable = "CONSTRUCTION_PM_S3_CONFIGURATION"
        if code.startswith("MISSING_DOCUMENT_STORAGE_CONFIGURATION:"):
            variable = code.split(":", 1)[1].split(",", 1)[0]
        errors.append(
            ConfigurationIssue(
                code.split(":", 1)[0] or "INVALID_DOCUMENT_STORAGE_CONFIGURATION",
                variable,
            )
        )
        problems.append("INVALID_DOCUMENT_STORAGE_CONFIGURATION")
        return False, problems
    return True, problems


def _validate_scanner(
    env: Mapping[str, str],
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
) -> tuple[bool, list[str]]:
    kind = _lower(env, "CONSTRUCTION_PM_SCANNER")
    problems: list[str] = []
    if not kind:
        if production:
            errors.append(
                ConfigurationIssue("MISSING_SCANNER", "CONSTRUCTION_PM_SCANNER")
            )
            problems.append("MISSING_SCANNER")
        return False, problems
    if kind not in {"reference", "external"}:
        errors.append(ConfigurationIssue("INVALID_SCANNER_KIND", "CONSTRUCTION_PM_SCANNER"))
        problems.append("INVALID_SCANNER_KIND")
        return False, problems
    strict = _lower(env, "CONSTRUCTION_PM_REQUIRE_SCANNED_CONTENT")
    if strict and strict not in {"1", "true", "yes", "on", "0", "false", "no", "off"}:
        errors.append(
            ConfigurationIssue(
                "INVALID_SCANNED_CONTENT_REQUIREMENT",
                "CONSTRUCTION_PM_REQUIRE_SCANNED_CONTENT",
            )
        )
        problems.append("INVALID_SCANNED_CONTENT_REQUIREMENT")
    if production and not strict:
        errors.append(
            ConfigurationIssue(
                "MISSING_SCANNED_CONTENT_REQUIREMENT",
                "CONSTRUCTION_PM_REQUIRE_SCANNED_CONTENT",
            )
        )
        problems.append("MISSING_SCANNED_CONTENT_REQUIREMENT")
    if production and strict and not _truth(strict):
        errors.append(
            ConfigurationIssue(
                "SCANNED_CONTENT_REQUIRED_IN_PRODUCTION",
                "CONSTRUCTION_PM_REQUIRE_SCANNED_CONTENT",
            )
        )
        problems.append("SCANNED_CONTENT_REQUIRED_IN_PRODUCTION")
    if production and kind == "reference":
        errors.append(
            ConfigurationIssue(
                "REFERENCE_SCANNER_FORBIDDEN_IN_PRODUCTION",
                "CONSTRUCTION_PM_SCANNER",
            )
        )
        problems.append("REFERENCE_SCANNER_FORBIDDEN_IN_PRODUCTION")
    if kind == "external":
        endpoint = _text(env, "CONSTRUCTION_PM_SCANNER_ENDPOINT")
        if not endpoint:
            errors.append(
                ConfigurationIssue(
                    "MISSING_SCANNER_ENDPOINT", "CONSTRUCTION_PM_SCANNER_ENDPOINT"
                )
            )
            problems.append("MISSING_SCANNER_ENDPOINT")
        elif not _validate_url(
            "CONSTRUCTION_PM_SCANNER_ENDPOINT",
            endpoint,
            production=production,
            errors=errors,
            warnings=warnings,
            require_https=True,
        ):
            problems.append("INVALID_SCANNER_ENDPOINT")
    return not problems, problems


def _validate_ocr(
    env: Mapping[str, str],
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
) -> tuple[bool, list[str]]:
    kind = _lower(env, "CONSTRUCTION_PM_OCR")
    problems: list[str] = []
    if not kind or kind == "disabled":
        return False, problems
    if kind not in {"reference", "external"}:
        errors.append(ConfigurationIssue("INVALID_OCR_KIND", "CONSTRUCTION_PM_OCR"))
        problems.append("INVALID_OCR_KIND")
        return False, problems
    if kind == "external":
        endpoint = _text(env, "CONSTRUCTION_PM_OCR_ENDPOINT")
        if not endpoint:
            errors.append(
                ConfigurationIssue("MISSING_OCR_ENDPOINT", "CONSTRUCTION_PM_OCR_ENDPOINT")
            )
            problems.append("MISSING_OCR_ENDPOINT")
            return False, problems
        if not _validate_url(
            "CONSTRUCTION_PM_OCR_ENDPOINT",
            endpoint,
            production=production,
            errors=errors,
            warnings=warnings,
            require_https=True,
        ):
            problems.append("INVALID_OCR_ENDPOINT")
            return False, problems
    return True, problems


def _validate_job_queue(
    env: Mapping[str, str],
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
) -> tuple[bool, list[str]]:
    kind = _lower(env, "CONSTRUCTION_PM_JOB_QUEUE")
    problems: list[str] = []
    if not kind:
        if production:
            errors.append(
                ConfigurationIssue("MISSING_JOB_QUEUE", "CONSTRUCTION_PM_JOB_QUEUE")
            )
            problems.append("MISSING_JOB_QUEUE")
        return False, problems
    if kind not in {"in_process", "durable"}:
        errors.append(ConfigurationIssue("INVALID_JOB_QUEUE_KIND", "CONSTRUCTION_PM_JOB_QUEUE"))
        problems.append("INVALID_JOB_QUEUE_KIND")
        return False, problems
    if production and kind == "in_process":
        errors.append(
            ConfigurationIssue(
                "IN_PROCESS_QUEUE_FORBIDDEN_IN_PRODUCTION",
                "CONSTRUCTION_PM_JOB_QUEUE",
            )
        )
        problems.append("IN_PROCESS_QUEUE_FORBIDDEN_IN_PRODUCTION")
        return False, problems
    return True, problems


def _validate_retention(
    env: Mapping[str, str],
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
) -> tuple[bool, list[str]]:
    kind = _lower(env, "CONSTRUCTION_PM_RETENTION")
    problems: list[str] = []
    if not kind:
        if production:
            errors.append(
                ConfigurationIssue("MISSING_RETENTION", "CONSTRUCTION_PM_RETENTION")
            )
            problems.append("MISSING_RETENTION")
        return False, problems
    if kind not in {"enabled", "disabled"}:
        errors.append(ConfigurationIssue("INVALID_RETENTION_KIND", "CONSTRUCTION_PM_RETENTION"))
        problems.append("INVALID_RETENTION_KIND")
        return False, problems
    if production and kind != "enabled":
        errors.append(
            ConfigurationIssue(
                "RETENTION_REQUIRED_IN_PRODUCTION", "CONSTRUCTION_PM_RETENTION"
            )
        )
        problems.append("RETENTION_REQUIRED_IN_PRODUCTION")
        return False, problems
    return kind == "enabled", problems


def _validate_observability(
    env: Mapping[str, str],
    *,
    production: bool,
    errors: list[ConfigurationIssue],
    warnings: list[ConfigurationIssue],
) -> tuple[bool, list[str]]:
    problems: list[str] = []
    log_format = _lower(env, "CONSTRUCTION_PM_LOG_FORMAT") or "text"
    if log_format not in {"json", "text"}:
        errors.append(
            ConfigurationIssue("INVALID_LOG_FORMAT", "CONSTRUCTION_PM_LOG_FORMAT")
        )
        problems.append("INVALID_LOG_FORMAT")
    if production and log_format != "json":
        errors.append(
            ConfigurationIssue("JSON_LOGS_REQUIRED_IN_PRODUCTION", "CONSTRUCTION_PM_LOG_FORMAT")
        )
        problems.append("JSON_LOGS_REQUIRED_IN_PRODUCTION")
    log_level = _lower(env, "CONSTRUCTION_PM_LOG_LEVEL") or "info"
    if log_level not in _LOG_LEVELS:
        errors.append(
            ConfigurationIssue("INVALID_LOG_LEVEL", "CONSTRUCTION_PM_LOG_LEVEL")
        )
        problems.append("INVALID_LOG_LEVEL")
    service_name = _text(env, "CONSTRUCTION_PM_SERVICE_NAME")
    if service_name and len(service_name) > 120:
        errors.append(
            ConfigurationIssue("INVALID_SERVICE_NAME", "CONSTRUCTION_PM_SERVICE_NAME")
        )
        problems.append("INVALID_SERVICE_NAME")
    endpoint = _text(env, "CONSTRUCTION_PM_OTEL_ENDPOINT")
    if endpoint and not _validate_url(
        "CONSTRUCTION_PM_OTEL_ENDPOINT",
        endpoint,
        production=production,
        errors=errors,
        warnings=warnings,
        require_https=True,
    ):
        problems.append("INVALID_OTEL_ENDPOINT")
    return not problems, problems


def validate_environment(
    environ: Mapping[str, str] | None = None,
    *,
    production: bool | None = None,
) -> EnvironmentValidation:
    """Validate operational configuration without printing any value."""
    env = os.environ if environ is None else environ
    is_production = _is_production(env, production)
    errors: list[ConfigurationIssue] = []
    warnings: list[ConfigurationIssue] = []

    environment = _lower(env, "CONSTRUCTION_PM_ENVIRONMENT") or (
        "production" if is_production else "development"
    )
    if environment not in KNOWN_ENVIRONMENTS:
        errors.append(
            ConfigurationIssue(
                "INVALID_ENVIRONMENT", "CONSTRUCTION_PM_ENVIRONMENT"
            )
        )

    database_configured, database_problems = _validate_database(
        env, production=is_production, errors=errors, warnings=warnings
    )
    storage_configured, storage_problems = _validate_storage(
        env, production=is_production, errors=errors, warnings=warnings
    )
    scanner_configured, scanner_problems = _validate_scanner(
        env, production=is_production, errors=errors, warnings=warnings
    )
    ocr_configured, ocr_problems = _validate_ocr(
        env, production=is_production, errors=errors, warnings=warnings
    )
    queue_configured, queue_problems = _validate_job_queue(
        env, production=is_production, errors=errors, warnings=warnings
    )
    retention_configured, retention_problems = _validate_retention(
        env, production=is_production, errors=errors, warnings=warnings
    )
    observability_ok, observability_problems = _validate_observability(
        env, production=is_production, errors=errors, warnings=warnings
    )

    return EnvironmentValidation(
        environment=environment,
        production=is_production,
        errors=tuple(errors),
        warnings=tuple(warnings),
        components={
            "database": database_configured,
            "object_storage": storage_configured,
            "malware_scanner": scanner_configured,
            "ocr": ocr_configured,
            "job_queue": queue_configured,
            "retention": retention_configured,
            "observability": observability_ok,
        },
        component_problems={
            "database": tuple(database_problems),
            "object_storage": tuple(storage_problems),
            "malware_scanner": tuple(scanner_problems),
            "ocr": tuple(ocr_problems),
            "job_queue": tuple(queue_problems),
            "retention": tuple(retention_problems),
            "observability": tuple(observability_problems),
        },
    )


@dataclass(frozen=True)
class ProbeResult:
    """A bounded, non-sensitive health observation from a deployment probe."""

    healthy: bool
    detail: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.healthy, bool):
            raise ProductionReadinessError("INVALID_PROBE_RESULT")
        if not isinstance(self.detail, str):
            raise ProductionReadinessError("INVALID_PROBE_DETAIL")


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    requirement: Requirement
    probe: Callable[[], object]

    def validate(self) -> None:
        if self.name not in COMPONENT_NAMES:
            raise ProductionReadinessError("INVALID_READINESS_COMPONENT")
        if not isinstance(self.requirement, Requirement):
            raise ProductionReadinessError("INVALID_READINESS_REQUIREMENT")
        if not callable(self.probe):
            raise ProductionReadinessError("INVALID_READINESS_PROBE")


@dataclass(frozen=True)
class ComponentReadiness:
    name: str
    requirement: Requirement
    healthy: bool
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "requirement": self.requirement.value,
            "status": "healthy" if self.healthy else "unhealthy",
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ReadinessReport:
    status: ReadinessStatus
    components: tuple[ComponentReadiness, ...]
    generated_at: str

    @property
    def ready(self) -> bool:
        return self.status in {ReadinessStatus.READY, ReadinessStatus.DEGRADED}

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "generated_at": self.generated_at,
            "components": [component.as_dict() for component in self.components],
        }


def _safe_detail(value: object, fallback: str) -> str:
    if isinstance(value, str) and _SAFE_DETAIL.match(value):
        return value
    return fallback


def _evaluate(probe: Callable[[], object]) -> ProbeResult:
    try:
        result = probe()
    except Exception as exc:  # noqa: BLE001 - a readiness probe must not crash the app
        return ProbeResult(False, f"PROBE_FAILED:{type(exc).__name__}")
    if isinstance(result, ProbeResult):
        return result
    if isinstance(result, bool):
        return ProbeResult(result, "OK" if result else "UNHEALTHY")
    return ProbeResult(False, "PROBE_RESULT_INVALID")


class ReadinessService:
    """Aggregate mandatory and optional component probes.

    A failed mandatory component is ``not_ready``. A failed optional component
    is ``degraded`` and still accepts traffic. Probe exception messages are
    never propagated; only the exception class name is recorded.
    """

    def __init__(self, checks: Iterable[ReadinessCheck], *, clock: Callable[[], datetime] | None = None) -> None:
        prepared = tuple(checks)
        seen: set[str] = set()
        for check in prepared:
            check.validate()
            if check.name in seen:
                raise ProductionReadinessError("DUPLICATE_READINESS_COMPONENT")
            seen.add(check.name)
        self._checks = prepared
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def report(self) -> ReadinessReport:
        components: list[ComponentReadiness] = []
        required_failed = False
        optional_failed = False
        for check in self._checks:
            result = _evaluate(check.probe)
            detail = _safe_detail(result.detail, "PROBE_DETAIL_REDACTED")
            if not result.healthy:
                if check.requirement is Requirement.REQUIRED:
                    required_failed = True
                else:
                    optional_failed = True
            components.append(
                ComponentReadiness(
                    name=check.name,
                    requirement=check.requirement,
                    healthy=result.healthy,
                    detail=detail,
                )
            )
        if required_failed:
            status = ReadinessStatus.NOT_READY
        elif optional_failed:
            status = ReadinessStatus.DEGRADED
        else:
            status = ReadinessStatus.READY
        return ReadinessReport(
            status=status,
            components=tuple(components),
            generated_at=self._clock().astimezone(timezone.utc).isoformat(),
        )


def build_readiness_service(
    environ: Mapping[str, str] | None = None,
    *,
    probes: Mapping[str, Callable[[], object]] | None = None,
    production: bool | None = None,
    clock: Callable[[], datetime] | None = None,
) -> ReadinessService:
    """Build the default readiness aggregation from validated environment configuration.

    Deployments should supply real probes for database connectivity, scanner
    availability and object-storage access. A required component without a real
    probe is reported unhealthy (``PROBE_NOT_CONFIGURED``) rather than assumed
    healthy.
    """
    validation = validate_environment(environ, production=production)
    provided = dict(probes or {})
    unknown = set(provided) - set(COMPONENT_NAMES)
    if unknown:
        raise ProductionReadinessError("UNKNOWN_READINESS_PROBE")
    checks: list[ReadinessCheck] = []

    def configuration_probe() -> ProbeResult:
        if validation.errors:
            return ProbeResult(False, validation.errors[0].code)
        if validation.warnings:
            return ProbeResult(True, "CONFIGURATION_WARNINGS")
        return ProbeResult(True, "CONFIGURATION_VALID")

    checks.append(
        ReadinessCheck(
            "configuration",
            Requirement.REQUIRED if validation.production else Requirement.OPTIONAL,
            configuration_probe,
        )
    )

    for name in COMPONENT_NAMES:
        if name == "configuration":
            continue
        requirement = (
            Requirement.OPTIONAL
            if name == "ocr"
            else (Requirement.REQUIRED if validation.production else Requirement.OPTIONAL)
        )
        problems = validation.component_problems.get(name, ())
        configured = bool(validation.components.get(name, False))
        probe = provided.get(name)
        if problems:
            def problem_probe(code: str = problems[0]) -> ProbeResult:
                return ProbeResult(False, code)

            checks.append(ReadinessCheck(name, requirement, problem_probe))
            continue
        if probe is not None:
            checks.append(ReadinessCheck(name, requirement, probe))
            continue
        if not configured:
            checks.append(
                ReadinessCheck(
                    name,
                    requirement,
                    lambda: ProbeResult(True, "NOT_CONFIGURED"),
                )
            )
            continue
        if requirement is Requirement.REQUIRED:
            checks.append(
                ReadinessCheck(
                    name,
                    requirement,
                    lambda: ProbeResult(False, "PROBE_NOT_CONFIGURED"),
                )
            )
            continue
        checks.append(
            ReadinessCheck(
                name,
                requirement,
                lambda: ProbeResult(True, "CONFIGURED_NOT_PROBED"),
            )
        )
    return ReadinessService(checks, clock=clock)


def normalize_correlation_id(value: object) -> str:
    """Return a safe correlation id, generating one when the input is absent/invalid."""
    if isinstance(value, str) and _CORRELATION_ID.match(value):
        return value
    return uuid.uuid4().hex


def correlation_id_from_environ(environ: Mapping[str, object]) -> str:
    return normalize_correlation_id(
        environ.get("HTTP_X_REQUEST_ID") or environ.get("HTTP_X_CORRELATION_ID")
    )


def _redact_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    text = _BEARER.sub(lambda match: f"{match.group(1)} [redacted]", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return text[:512]


def redact_fields(fields: Mapping[str, object] | None) -> dict[str, object]:
    """Return a bounded copy with sensitive keys removed."""
    if not fields:
        return {}
    redacted: dict[str, object] = {}
    for key, value in fields.items():
        name = str(key)
        lowered = name.lower()
        if any(part in lowered for part in _REDACT_KEY_PARTS):
            redacted[name] = "[redacted]"
        else:
            redacted[name] = _redact_value(value)
    return redacted


class StructuredEventLogger:
    """Emit one JSON object per line, with correlation id and no sensitive fields."""

    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        service: str = "construction-pm",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(service, str) or not service.strip() or len(service) > 120:
            raise ProductionReadinessError("INVALID_SERVICE_NAME")
        self._stream = stream or sys.stderr
        self._service = service.strip()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def event_dict(
        self,
        event: str,
        *,
        severity: str = "info",
        correlation_id: object = None,
        fields: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        if not isinstance(event, str) or not event.strip() or len(event) > 120:
            raise ProductionReadinessError("INVALID_EVENT_NAME")
        level = severity.lower()
        if level not in _LOG_LEVELS:
            raise ProductionReadinessError("INVALID_LOG_LEVEL")
        payload: dict[str, object] = {
            "timestamp": self._clock().astimezone(timezone.utc).isoformat(),
            "severity": level,
            "service": self._service,
            "event": event,
            "correlation_id": normalize_correlation_id(correlation_id),
        }
        payload.update(redact_fields(fields))
        return payload

    def emit(
        self,
        event: str,
        *,
        severity: str = "info",
        correlation_id: object = None,
        fields: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        payload = self.event_dict(
            event,
            severity=severity,
            correlation_id=correlation_id,
            fields=fields,
        )
        self._stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        self._stream.flush()
        return payload


__all__ = [
    "COMPONENT_NAMES",
    "ComponentReadiness",
    "ConfigurationIssue",
    "EnvironmentValidation",
    "KNOWN_ENVIRONMENTS",
    "PRODUCTION_ENVIRONMENTS",
    "ProbeResult",
    "ProductionReadinessError",
    "ReadinessCheck",
    "ReadinessReport",
    "ReadinessService",
    "ReadinessStatus",
    "Requirement",
    "StructuredEventLogger",
    "build_readiness_service",
    "correlation_id_from_environ",
    "normalize_correlation_id",
    "redact_fields",
    "validate_environment",
]
