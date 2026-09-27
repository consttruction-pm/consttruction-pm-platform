import pytest

from construction_pm.postgres_hardening import (
    PostgresHardeningError,
    PostgresTimeoutPolicy,
    apply_postgres_timeout_policy,
)


class FakeConnection:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))


def test_timeout_policy_uses_transaction_local_limits():
    conn = FakeConnection()
    apply_postgres_timeout_policy(
        conn, PostgresTimeoutPolicy(statement_timeout_ms=1000, lock_timeout_ms=200, idle_in_transaction_timeout_ms=3000)
    )
    assert conn.calls == [
        ("SET LOCAL statement_timeout = %s", (1000,)),
        ("SET LOCAL lock_timeout = %s", (200,)),
        ("SET LOCAL idle_in_transaction_session_timeout = %s", (3000,)),
    ]


@pytest.mark.parametrize(
    "field",
    ["statement_timeout_ms", "lock_timeout_ms", "idle_in_transaction_timeout_ms"],
)
def test_timeout_policy_rejects_non_positive_values(field):
    values = {
        "statement_timeout_ms": 1,
        "lock_timeout_ms": 1,
        "idle_in_transaction_timeout_ms": 1,
    }
    values[field] = 0
    with pytest.raises(PostgresHardeningError, match=f"INVALID_POSTGRES_{field.upper()}"):
        PostgresTimeoutPolicy(**values).validate()


def test_timeout_policy_rejects_bool_as_integer():
    with pytest.raises(PostgresHardeningError, match="INVALID_POSTGRES_LOCK_TIMEOUT_MS"):
        PostgresTimeoutPolicy(lock_timeout_ms=True).validate()
