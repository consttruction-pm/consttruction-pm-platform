from construction_pm.resources.transactions import NoOpTransactionManager

def test_transaction_context_propagates_failure_without_hidden_commit():
    manager = NoOpTransactionManager()
    events = []
    try:
        with manager.transaction():
            events.append("write-1")
            raise RuntimeError("abort")
    except RuntimeError:
        pass
    assert events == ["write-1"]
