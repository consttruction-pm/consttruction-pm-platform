from contextlib import contextmanager
from typing import Any, Protocol

class TransactionalConnection(Protocol):
    def commit(self) -> Any: ...
    def rollback(self) -> Any: ...

class PostgresTransactionManager:
    def __init__(self, connection: TransactionalConnection):
        self.connection=connection

    @contextmanager
    def transaction(self):
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
