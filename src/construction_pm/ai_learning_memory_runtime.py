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

    Runtime and migration DSNs are excluded from repr and error messages. Remote
    deployments must use different database roles for runtime DML and migrations.
    An unset/disabled backend never silently falls back to SQLite.
    """

    database_url: str = field(repr=False)
    migration_database_url: str | None = field(default=None, repr=False)
    connect_timeout_seconds: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.database_url, str) or not self.database_url.strip():
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_URL_REQUIRED"
            )
        _validate_postgres_dsn(self.database_url)
        runtime_parts = urlsplit(self.database_url)
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        is_remote = (runtime_parts.hostname or "").lower() not in local_hosts

        if self.migration_database_url is not None:
            if (
                not isinstance(self.migration_database_url, str)
                or not self.migration_database_url.strip()
            ):
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_MIGRATION_DATABASE_URL_INVALID"
                )
            _validate_postgres_dsn(self.migration_database_url)
            migration_parts = urlsplit(self.migration_database_url)
            same_target = (
                runtime_parts.hostname == migration_parts.hostname
                and runtime_parts.port == migration_parts.port
                and runtime_parts.path == migration_parts.path
            )
            if not same_target:
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_MIGRATION_DATABASE_TARGET_MISMATCH"
                )
            if runtime_parts.username == migration_parts.username:
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_DATABASE_ROLE_SEPARATION_REQUIRED"
                )
        elif is_remote:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_MIGRATION_DATABASE_URL_REQUIRED"
            )

        if (
            isinstance(self.connect_timeout_seconds, bool)
            or not isinstance(self.connect_timeout_seconds, int)
            or not 1 <= self.connect_timeout_seconds <= 30
        ):
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_CONNECT_TIMEOUT_INVALID"
            )

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
        migration_dsn = values.get(
            "CUBI_AI_LEARNING_MEMORY_MIGRATION_DATABASE_URL", ""
        ).strip() or None

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
        return cls(
            database_url=dsn,
            migration_database_url=migration_dsn,
            connect_timeout_seconds=timeout,
        )

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
        except Exception as exc:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_DRIVER_UNAVAILABLE"
            ) from exc

        migration_url = config.migration_database_url or config.database_url
        migration_connection = None
        try:
            migration_connection = psycopg.connect(
                migration_url,
                connect_timeout=config.connect_timeout_seconds,
                application_name="cubi-ai-learning-memory-migrations",
                autocommit=False,
            )
            PostgresAILearningMemoryRepository(
                migration_connection
            ).initialize()
            migration_connection.rollback()
        except Exception as exc:
            if migration_connection is not None:
                try:
                    migration_connection.rollback()
                finally:
                    migration_connection.close()
            if isinstance(exc, AILearningMemoryRuntimeError):
                raise
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_SCHEMA_INITIALIZATION_FAILED"
            ) from exc
        finally:
            if migration_connection is not None and not migration_connection.closed:
                migration_connection.close()

        try:
            connection = psycopg.connect(
                config.database_url,
                connect_timeout=config.connect_timeout_seconds,
                application_name="cubi-ai-learning-memory",
                autocommit=False,
            )
        except Exception as exc:
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_CONNECTION_FAILED"
            ) from exc

        repository = PostgresAILearningMemoryRepository(connection)
        try:
            permissions = connection.execute(
                """
                SELECT
                    current_setting('transaction_read_only'),
                    has_table_privilege(current_user, 'ai_learning_memory_records', 'SELECT'),
                    has_table_privilege(current_user, 'ai_learning_memory_records', 'INSERT'),
                    has_table_privilege(current_user, 'ai_learning_memory_records', 'UPDATE'),
                    has_table_privilege(current_user, 'ai_learning_memory_records', 'DELETE'),
                    has_table_privilege(current_user, 'ai_learning_memory_audit_events', 'SELECT'),
                    has_table_privilege(current_user, 'ai_learning_memory_audit_events', 'INSERT'),
                    has_table_privilege(current_user, 'ai_learning_memory_audit_events', 'UPDATE'),
                    has_table_privilege(current_user, 'ai_learning_memory_audit_events', 'DELETE')
                """
            ).fetchone()
            if permissions is None or str(permissions[0]).lower() != "off":
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_DATABASE_MUST_BE_WRITABLE"
                )
            if not all(bool(value) for value in (permissions[1], permissions[2], permissions[5], permissions[6])):
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_DATABASE_RUNTIME_ROLE_PRIVILEGES_INCOMPLETE"
                )
            if (
                config.migration_database_url is not None
                and any(bool(value) for value in (permissions[3], permissions[4], permissions[7], permissions[8]))
            ):
                raise AILearningMemoryRuntimeError(
                    "AI_LEARNING_DATABASE_RUNTIME_ROLE_PRIVILEGE_TOO_BROAD"
                )
            # Leave the long-lived application connection idle after its probe.
            connection.rollback()
        except Exception as exc:
            try:
                connection.rollback()
            finally:
                connection.close()
            if isinstance(exc, AILearningMemoryRuntimeError):
                raise
            raise AILearningMemoryRuntimeError(
                "AI_LEARNING_DATABASE_RUNTIME_PRIVILEGE_CHECK_FAILED"
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
