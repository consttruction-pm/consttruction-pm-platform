from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager

class Connection:
    def __init__(self): self.commits=0; self.rollbacks=0
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1

def test_transaction_commits():
    c=Connection()
    with PostgresTransactionManager(c).transaction(): pass
    assert (c.commits,c.rollbacks)==(1,0)

def test_transaction_rolls_back():
    c=Connection()
    try:
        with PostgresTransactionManager(c).transaction():
            raise RuntimeError("boom")
    except RuntimeError: pass
    assert (c.commits,c.rollbacks)==(0,1)
