"""Compatibility adapters for the legacy Resource transaction import path.

Production Resource application code uses construction_pm.backend_p0.transactions.
Keep NoOpTransactionManager for existing tests and callers that need a test-only
no-op boundary; new production code must not import this module.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from ..backend_p0.transactions import SQLiteTransactionManager


class TransactionManager(Protocol):
    """Compatibility protocol; canonical production boundary lives in backend_p0."""

    def transaction(self) -> AbstractContextManager[None]: ...


class NoOpTransactionManager:
    """Test adapter; production code should use backend_p0.transactions."""

    def transaction(self) -> AbstractContextManager[None]:
        return _NoOpTransaction()


class _NoOpTransaction(AbstractContextManager[None]):
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False


__all__ = ["TransactionManager", "SQLiteTransactionManager", "NoOpTransactionManager"]
