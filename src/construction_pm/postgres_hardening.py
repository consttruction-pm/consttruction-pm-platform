from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class PostgresHardeningError(ValueError):
    pass


class PostgresSession(Protocol):
    def execute(self, sql: str, params: tuple[object, ...] = ()): ...


@dataclass(frozen=True)
class PostgresTimeoutPolicy:
    statement_timeout_ms: int = 30_000
    lock_timeout_ms: int = 5_000
    idle_in_transaction_timeout_ms: int = 60_000

    def validate(self) -> None:
        for name, value in (
            ("statement_timeout_ms", self.statement_timeout_ms),
            ("lock_timeout_ms", self.lock_timeout_ms),
            ("idle_in_transaction_timeout_ms", self.idle_in_transaction_timeout_ms),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise PostgresHardeningError(f"INVALID_POSTGRES_{name.upper()}")


def apply_postgres_timeout_policy(
    connection: PostgresSession, policy: PostgresTimeoutPolicy = PostgresTimeoutPolicy()
) -> None:
    """Apply transaction-local safety limits; caller owns the surrounding transaction."""
    policy.validate()
    connection.execute("SET LOCAL statement_timeout = %s", (policy.statement_timeout_ms,))
    connection.execute("SET LOCAL lock_timeout = %s", (policy.lock_timeout_ms,))
    connection.execute(
        "SET LOCAL idle_in_transaction_session_timeout = %s",
        (policy.idle_in_transaction_timeout_ms,),
    )
