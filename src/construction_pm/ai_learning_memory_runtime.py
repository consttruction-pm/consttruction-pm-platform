from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import parse_qs, urlsplit

from .ai_learning_memory_repository import (
    AILearningMemoryPersistenceError,
    PostgresAILearningMemoryRepository,
)


class AILearningMemoryRuntimeError(RuntimeError):
    """Sanitized configuration, connection or migration failure."""


@dataclass(frozen=True)
class PostgresAILearningMemoryConfig:
    """Explicit server-side PostgreSQL configuration for durable AI memory.

    The DSN is intentionally excluded from repr and error messages. An unset or
    disabled backend returns no runtime; it never silently falls back to SQLite.
    """

    database_url: str = field(repr=False)
    connect_timeout_seconds: int = 10

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> PostgresAILearningMemoryConfig | None:
        values = os.environ if environment is None else environment
        backend = values.get("CUBI_AI_LEARNING_MEMORY_DB_BACKEND", "disabled")
        backend = backend.strip().lower()
        if backend in {"", "disabled", "off", "false", "0"}:
            return None
        if backend not in {"postgres", "postgresql"}:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_BACKEND_UNSUPPORTED"
            )

        dsn = values.get("CUBI_AI_LEARNING_MEMORY_DATABASE_URL", "").strip()
        if not dsn:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_URL_REQUIRED"
            )
        _validate_postgres_dsn(dsn)

        raw_timeout = values.get(
            "CUBI_AI_LEARNING_MEMORY_CONNECT_TIMEOUT_SECONDS", "10"
        ).strip()
        try:
            timeout = int(raw_timeout)
        except (TypeError, ValueError) as exc:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_CONNECT_TIMEOUT_INVALID"
            ) from exc
        if not 1 <= timeout <= 30:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_CONNECT_TIMEOUT_INVALID"
            )
        return cls(database_url=dsn, connect_timeout_seconds=timeout)


def _validate_postgres_dsn(dsn: str) -> None:
    try:
        parsed = urlsplit(dsn)
        host = parsed.hostname
        port = parsed.port
        query = parse_qs(parsed.query, keep_blank_values=True)
    except ValueError as exc:
        raise AILearningMemoryRuntimeError(
            "AI_LEARNING_DATABASE_URL_INVALID"
        ) from exc

    if (
        parsed.scheme.lower() not in {"postgres", "postgresql"}
        or not parsed.netloc
        or not host
        or parsed.username is None
        or not parsed.path.strip("/")
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise AILearningMemoryRuntimeError(
            "AI_LEARNING_DATABASE_URL_INVALID"
        )

    ssl_modes = query.get("sslmode", [])
    if len(ssl_modes) > 1:
        raise AILearningMemoryRuntimeError(
            "AI_LEARNING_DATABASE_SSLMODE_INVALID"
        )
    ssl_mode = ssl_modes[0].lower() if ssl_modes else None
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if host.lower() not in local_hosts and ssl_mode not in {
        "require",
        "verify-ca",
        "verify-full",
    }:
        raise AILearningMemoryRuntimeError(
            "AI_LEARNING_DATABASE_TLS_REQUIRED"
        )
    if ssl_mode is not None and ssl_mode not in {
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    }:
        raise AILearningMemoryRuntimeError(
            "AI_LEARNING_DATABASE_SSLMODE_INVALID"
        )


@dataclass
class PostgresAILearningMemoryRuntime:
    """Owns one durable PostgreSQL connection for the application lifetime."""

    connection: object = field(repr=False)
    repository: PostgresAILearningMemoryRepository
    _closed: bool = field(default=False, init=False, repr=False)

    @classmethod
    def open(
        cls,
        config: PostgresAILearningMemoryConfig,
    ) -> PostgresAILearningMemoryRuntime:
        if not isinstance(config, PostgresAILearningMemoryConfig):
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_CONFIGURATION_REQUIRED"
            )
        try:
            import psycopg

            connection = psycopg.connect(
                config.database_url,
                connect_timeout=config.connect_timeout_seconds,
                application_name="cubi-ai-learning-memory",
                autocommit=False,
            )
        except Exception as exc:
            # Never include the DSN or driver error text in the public message.
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_CONNECTION_FAILED"
            ) from exc

        repository = PostgresAILearningMemoryRepository(connection)
        try:
            repository.initialize()
            row = connection.execute(
                "SELECT current_setting('transaction_read_only')"
            ).fetchone()
            if row is None or str(row[0]).lower() != "off":
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_DATABASE_MUST_BE_WRITABLE"
                )
            # Leave the long-lived connection idle after its startup probe.
            connection.rollback()
        except Exception as exc:
            try:
                connection.rollback()
            finally:
                connection.close()
            if isinstance(exc, AILearningMemoryRuntimeError):
                raise
            if isinstance(exc, AILearningMemoryPersistenceError):
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_DATABASE_SCHEMA_INITIALIZATION_FAILED"
                ) from exc
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_STARTUP_CHECK_FAILED"
            ) from exc
        return cls(connection=connection, repository=repository)

    @classmethod
    def open_from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> PostgresAILearningMemoryRuntime | None:
        config = PostgresAILearningMemoryConfig.from_environment(environment)
        if config is None:
            return None
        return cls.open(config)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.connection.rollback()
        finally:
            self.connection.close()

    def __enter__(self) -> PostgresAILearningMemoryRuntime:
        if self._closed:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_RUNTIME_CLOSED"
            )
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


__all__ = [
    "AILearningMemoryRuntimeError",
    "PostgresAILearningMemoryConfig",
    "PostgresAILearningMemoryRuntime",
]
