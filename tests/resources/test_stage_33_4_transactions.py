import sqlite3

import pytest

from construction_pm.resources.persistence import SQLiteResourceRepository
from construction_pm.resources.transactions import SQLiteTransactionManager


def test_application_transaction_adapter_rolls_back_repository_mutation():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteResourceRepository(connection)
    manager = SQLiteTransactionManager(connection)

    with pytest.raises(RuntimeError):
        with manager.transaction():
            repository.connection.execute(
                "INSERT INTO resources "
                "(id, code, name, resource_type, unit, active, revision) "
                "VALUES ('R-1', 'LAB', 'Labor', 'labor', 'hour', 1, 1)"
            )
            raise RuntimeError("abort")

    assert repository.get_resource("R-1") is None


def test_repository_transaction_participates_in_existing_application_transaction():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteResourceRepository(connection)
    manager = SQLiteTransactionManager(connection)

    with manager.transaction():
        repository.connection.execute(
            "INSERT INTO resources "
            "(id, code, name, resource_type, unit, active, revision) "
            "VALUES ('R-1', 'LAB', 'Labor', 'labor', 'hour', 1, 1)"
        )
        with repository.transaction():
            repository.connection.execute(
                "UPDATE resources SET code='LAB-2' WHERE id='R-1'"
            )
        assert repository.connection.in_transaction

    row = connection.execute("SELECT code FROM resources WHERE id='R-1'").fetchone()
    assert row == ("LAB-2",)
