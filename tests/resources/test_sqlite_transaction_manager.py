import sqlite3
import pytest

from construction_pm.resources.persistence import SQLiteResourceRepository
from construction_pm.resources.transactions import SQLiteTransactionManager


def test_sqlite_transaction_manager_commits_and_rolls_back_atomically():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteResourceRepository(connection)
    manager = SQLiteTransactionManager(connection)

    with manager.transaction():
        connection.execute("INSERT INTO resources (id,code,name,resource_type,unit,calendar_id,active,revision) VALUES ('r1','LAB-1','Crew','labor','hour',NULL,1,1)")
    assert repository.get_resource("r1") is not None

    with pytest.raises(RuntimeError):
        with manager.transaction():
            connection.execute("UPDATE resources SET name='Changed' WHERE id='r1'")
            raise RuntimeError("abort")
    assert repository.get_resource("r1").name == "Crew"


def test_nested_failure_rolls_back_outer_transaction():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteResourceRepository(connection)
    manager = SQLiteTransactionManager(connection)
    with pytest.raises(RuntimeError):
        with manager.transaction():
            connection.execute("INSERT INTO resources (id,code,name,resource_type,unit,calendar_id,active,revision) VALUES ('r1','LAB-1','Crew','labor','hour',NULL,1,1)")
            with manager.transaction():
                raise RuntimeError("abort")
    assert repository.get_resource("r1") is None
