from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

class TransactionManager(Protocol):
    """Application-level transaction boundary."""
    def transaction(self) -> AbstractContextManager[None]: ...

class NoOpTransactionManager:
    """Test adapter; production adapters provide real atomicity."""
    def transaction(self) -> AbstractContextManager[None]:
        return _NoOpTransaction()

class _NoOpTransaction(AbstractContextManager[None]):
    def __enter__(self) -> None: return None
    def __exit__(self, exc_type, exc_value, traceback) -> bool: return False
