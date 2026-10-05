from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager
from typing import Protocol


class TransactionManager(Protocol):
    """Application-level transaction boundary."""
    def transaction(self) -> AbstractContextManager[None]: ...


class NoOpTransactionManager:
    """Test adapter; production adapters provide real atomicity."""
    def transaction(self) -> AbstractContextManager[None]:
        return _NoOpTransaction()


class SQLiteTransactionManager:
    """Application-owned SQLite transaction boundary with nested participation."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._savepoint_counter = 0

    def transaction(self) -> AbstractContextManager[None]:
        return _SQLiteTransaction(self.connection, self)


class _NoOpTransaction(AbstractContextManager[None]):
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False


class _SQLiteTransaction(AbstractContextManager[None]):
    def __init__(self, connection: sqlite3.Connection, manager: SQLiteTransactionManager) -> None:
        self.connection = connection
        self.manager = manager
        self._owner = False
        self._savepoint: str | None = None

    def __enter__(self) -> None:
        if self.connection.in_transaction:
            self.manager._savepoint_counter += 1
            self._savepoint = f"construction_pm_sp_{self.manager._savepoint_counter}"
            self.connection.execute(f"SAVEPOINT {self._savepoint}")
        else:
            self.connection.execute("BEGIN")
            self._owner = True
        return None

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if self._savepoint is not None:
            if exc_type is None:
                self.connection.execute(f"RELEASE SAVEPOINT {self._savepoint}")
            else:
                self.connection.execute(f"ROLLBACK TO SAVEPOINT {self._savepoint}")
                self.connection.execute(f"RELEASE SAVEPOINT {self._savepoint}")
            return False
        if self._owner:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        return False
