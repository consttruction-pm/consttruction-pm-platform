from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager, contextmanager
from typing import Iterator, Protocol


class TransactionManager(Protocol):
    """Application-level transaction boundary."""
    def transaction(self) -> AbstractContextManager[None]: ...


class NoOpTransactionManager:
    """Test adapter; production adapters provide real atomicity."""
    def transaction(self) -> AbstractContextManager[None]:
        return _NoOpTransaction()


class SQLiteTransactionManager:
    """Application transaction adapter backed by one SQLite connection."""
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self.connection.in_transaction:
            yield None
            return
        self.connection.execute("BEGIN")
        try:
            yield None
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()


class _NoOpTransaction(AbstractContextManager[None]):
    def __enter__(self) -> None:
        return None
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False
