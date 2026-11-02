from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager
from typing import Protocol


def execute_sqlite_script(connection: sqlite3.Connection, script: str) -> None:
    """Execute SQL statements without sqlite3.executescript's implicit COMMIT.

    Connection.executescript commits any pending transaction before executing
    the script. That breaks caller-owned atomic units such as a local domain
    write plus outbox append. This helper uses SQLite's complete-statement
    parser and execute so statements participate in the active transaction.
    """
    if not isinstance(script, str) or not script.strip():
        raise ValueError("SQLITE_SCRIPT_REQUIRED")
    pending: list[str] = []
    for line in script.splitlines():
        pending.append(line)
        statement = "\n".join(pending)
        if sqlite3.complete_statement(statement):
            if statement.strip():
                connection.execute(statement)
            pending.clear()
    remainder = "\n".join(pending).strip()
    if remainder:
        raise ValueError("INCOMPLETE_SQLITE_SCRIPT")


class TransactionManager(Protocol):
    def transaction(self) -> AbstractContextManager[None]: ...


class SQLiteTransactionManager:
    """Application-owned transaction boundary; outer transactions use BEGIN IMMEDIATE."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self._savepoint_counter = 0

    def transaction(self) -> AbstractContextManager[None]:
        return _SQLiteTransaction(self)


class _SQLiteTransaction(AbstractContextManager[None]):
    def __init__(self, manager: SQLiteTransactionManager) -> None:
        self.manager = manager
        self.connection = manager.connection
        self._owner = False
        self._savepoint: str | None = None

    def __enter__(self) -> None:
        if self.connection.in_transaction:
            self.manager._savepoint_counter += 1
            self._savepoint = f"backend_p0_sp_{self.manager._savepoint_counter}"
            self.connection.execute(f"SAVEPOINT {self._savepoint}")
        else:
            self.connection.execute("BEGIN IMMEDIATE")
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
